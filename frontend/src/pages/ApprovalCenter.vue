<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { approveProposal, fetchProposals } from '../api/client'
import { useAuth } from '../stores/auth'

const auth = useAuth()

const stages = [
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '課長/部長' },
  { value: 'committee', label: '改善委員' },
]
const classificationOptions = [
  { value: '保留提案', label: '保留提案' },
  { value: '努力提案', label: '努力提案' },
  { value: 'アイディア提案', label: 'アイディア提案' },
  { value: '優秀提案', label: '優秀提案' },
]
const selectedStage = ref(null)
const proposals = ref([])
const selectedProposal = ref(null)
const loading = ref(false)
const message = ref('')
const dialogOpen = ref(false)

const contributorsOf = (proposal) => {
  const list = proposal?.contributors || []
  return list
    .filter((c) => c.is_primary !== true)
    .map((c, idx) => ({
      key: `${c.employee?.id || c.employee || c.employee_code || idx}`,
      name: c.employee?.name || c.employee_name || '未設定',
      code: c.employee?.code || c.employee_code || '',
      share: c.share_percent ?? '',
      primary: Boolean(c.is_primary),
    }))
}

const formatShare = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : ''
}

const effectDepartments = (proposal) => {
  const raw = proposal?.contribution_business
  if (Array.isArray(raw)) return raw.filter(Boolean).join('、')
  if (typeof raw === 'string') {
    return raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .join('、')
  }
  return ''
}

const form = reactive({
  status: 'approved',
  confirmed_name: '',
  comment: '',
  mindset: 3,
  idea: 3,
  hint: 3,
  sdgs_flag: false,
  safety_flag: false,
  term: '',
  quarter: '',
  proposal_classification: '',
  committee_classification: '',
})

const needsScore = (stage) => stage === 'manager'

const classificationValues = {
  hold: classificationOptions[0]?.value ?? '',
  effort: classificationOptions[1]?.value ?? '',
  idea: classificationOptions[2]?.value ?? '',
  excellent: classificationOptions[3]?.value ?? '',
}

const classificationTouched = ref(false)

const classificationPoints = computed(() => {
  const map = {
    [classificationValues.hold]: 0,
    [classificationValues.effort]: 1,
    [classificationValues.idea]: 4,
    [classificationValues.excellent]: 8,
  }
  const points = map[form.proposal_classification]
  return points ?? ''
})

const suggestClassification = () => {
  const scores = [form.mindset, form.idea, form.hint]
  const validScores = scores.filter((v) => v !== null && v !== undefined && v !== '')
  if (validScores.length === 0) return ''

  const count5 = validScores.filter((v) => Number(v) === 5).length
  if (count5 >= 1) return classificationValues.excellent

  const count4 = validScores.filter((v) => Number(v) === 4).length
  if (count4 >= 2) return classificationValues.idea

  return classificationValues.effort
}

const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ja-JP') : '')

const stageApproval = (stage) => {
  const approvals = selectedProposal.value?.approvals || []
  return approvals.find((a) => a.stage === stage)
}

const proposalPointShare = computed(() => {
  const proposal = selectedProposal.value
  const contributors = proposal?.contributors || []
  const shares = contributors
    .map((c) => Number(c.classification_points_share))
    .filter((v) => Number.isFinite(v) && v > 0)
  if (shares.length) {
    const total = shares.reduce((a, b) => a + b, 0)
    return { share: shares[0], total }
  }
  const total = Number(proposal?.classification_points)
  if (!Number.isFinite(total)) return { share: null, total: null }
  const contributorCount = Math.max(contributors.length || 1, 1)
  return { share: total / contributorCount, total }
})

const orderedStages = ['supervisor', 'chief', 'manager', 'committee']

const allowedStages = computed(() => {
  // UserProfileベース（新システム）とEmployeeベース（旧システム）の両方に対応
  const role = auth.state.employee?.profile?.role || auth.state.employee?.role
  switch (role) {
    case 'supervisor':
      return ['supervisor']
    case 'chief':
      return ['supervisor', 'chief']
    case 'manager':
      return ['supervisor', 'chief', 'manager']
    case 'committee':
    case 'committee_chair':
      return ['committee']
      // return ['supervisor', 'chief', 'manager', 'committee']
    case 'admin':
      return ['supervisor', 'chief', 'manager', 'committee']
    default:
      return []
  }
})

const visibleStages = computed(() => {
  const allowed = allowedStages.value
  return allowed.length ? stages.filter((s) => allowed.includes(s.value)) : []
})

const preferredStageForRole = () => {
  const role = auth.state.employee?.profile?.role || auth.state.employee?.role
  const preferredByRole = {
    supervisor: 'supervisor',
    chief: 'chief',
    manager: 'manager',
    committee: 'committee',
    committee_chair: 'committee',
  }
  const preferred = preferredByRole[role]
  if (preferred && allowedStages.value.includes(preferred)) {
    return preferred
  }
  return visibleStages.value[0]?.value ?? null
}

const isCommitteeStage = computed(() => selectedStage.value === 'committee')
const isManagerStage = computed(() => selectedStage.value === 'manager')

const lowerStagesApproved = (proposal) => {
  const current = selectedStage.value
  const idx = orderedStages.indexOf(current)
  if (idx <= 0) return true
  const required = orderedStages.slice(0, idx)
  const approvals = Array.isArray(proposal.approvals) ? proposal.approvals : []
  return required.every((stage) => approvals.find((a) => a.stage === stage)?.status === 'approved')
}

const isCurrentStageApproved = (proposal) => {
  const current = selectedStage.value
  if (!current) return false
  const approvals = Array.isArray(proposal.approvals) ? proposal.approvals : []
  const approval = approvals.find((a) => a.stage === current)
  return approval?.status === 'approved'
}

const ensureStage = () => {
  if (visibleStages.value.length === 0) {
    selectedStage.value = null
    return false
  }
  if (!selectedStage.value || !allowedStages.value.includes(selectedStage.value)) {
    selectedStage.value = preferredStageForRole()
  }
  return !!selectedStage.value
}

// ログインユーザーの役割と所属に応じてフィルタリング
const filteredProposals = computed(() => {
  // UserProfileベース（新システム）またはEmployeeベース（旧システム）に対応
  const userProfile = auth.state.employee?.profile || auth.state.employee
  const role = userProfile?.role
  const dept = userProfile?.responsible_department || userProfile?.department

  // システム管理者は全ての提案を閲覧可能
  if (role === 'admin') {
    return proposals.value.filter((p) => lowerStagesApproved(p) && !isCurrentStageApproved(p))
  }

  if (!role || !dept) {
    return proposals.value.filter((p) => lowerStagesApproved(p) && !isCurrentStageApproved(p))
  }

  return proposals.value.filter(proposal => {
    // 現在のステージで既に承認済みの提案は除外
    if (isCurrentStageApproved(proposal)) return false

    // 下位ステージの承認チェック
    if (!lowerStagesApproved(proposal)) return false

    switch (role) {
      case 'supervisor':
        return proposal.team === dept
      case 'chief':
        return proposal.group === dept
      case 'manager':
        return (proposal.department === dept || proposal.section === dept)
      case 'committee':
      case 'committee_chair':
        return (proposal.department === dept || proposal.section === dept)
      default:
        return true
    }
  })
})

const loadProposals = async () => {
  if (!ensureStage()) {
    proposals.value = []
    selectedProposal.value = null
    message.value = 'このユーザーは承認ステージの権限がありません'
    return
  }
  loading.value = true
  message.value = ''
  try {
    proposals.value = await fetchProposals({ stage: selectedStage.value, status: 'pending' })
    if (selectedProposal.value) {
      // 選択中の提案を更新
      const updated = filteredProposals.value.find(p => p.id === selectedProposal.value.id)
      if (updated) {
        selectedProposal.value = updated
      } else {
        selectedProposal.value = null
      }
    }
  } catch (error) {
    message.value = error.message ?? '承認待ち一覧の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const selectProposal = (proposal) => {
  if (!ensureStage()) return
  selectedProposal.value = proposal
}

const closeDetail = () => {
  selectedProposal.value = null
}

const normalizedImages = (kind) => {
  const proposal = selectedProposal.value
  if (!proposal) return []
  const key = `${kind}_images`
  const images = Array.isArray(proposal[key]) ? proposal[key] : []
  if (images.length > 0) return images
  const singlePath = proposal[`${kind}_image_path`]
  return singlePath ? [{ id: `legacy-${kind}`, url: singlePath, path: singlePath, filename: singlePath }] : []
}

const beforeImages = computed(() => normalizedImages('before'))
const afterImages = computed(() => normalizedImages('after'))

const canActOnCurrentStage = computed(() => {
  return !!selectedStage.value && allowedStages.value.includes(selectedStage.value)
})

const openApprovalDialog = () => {
  if (!selectedProposal.value) return
  if (!ensureStage()) return
  dialogOpen.value = true
  form.status = 'approved'
  form.confirmed_name = auth.state.employee?.name || auth.state.user?.username || ''
  form.comment = ''
  form.mindset = selectedProposal.value?.mindset_score ?? 3
  form.idea = selectedProposal.value?.idea_score ?? 3
  form.hint = selectedProposal.value?.hint_score ?? 3
  const managerApproval = stageApproval('manager') || {}
  form.sdgs_flag = Boolean(managerApproval.sdgs_flag)
  form.safety_flag = Boolean(managerApproval.safety_flag)
  form.term = selectedProposal.value?.term ?? ''
  form.quarter = selectedProposal.value?.quarter ?? ''
  classificationTouched.value = false
  form.proposal_classification = selectedProposal.value?.proposal_classification ?? ''
  if (isManagerStage.value) {
    if (form.proposal_classification) {
      classificationTouched.value = true
    } else {
      form.proposal_classification = suggestClassification()
    }
  }
  form.committee_classification = selectedProposal.value?.committee_classification ?? ''
}

const closeDialog = () => {
  dialogOpen.value = false
}

const submitApproval = async () => {
  if (!form.confirmed_name) {
    message.value = '承認者氏名を入力してください'
    return
  }
  if (!canActOnCurrentStage.value) {
    message.value = 'このステージの承認権限がありません'
    return
  }
  if (isManagerStage.value && form.status === 'approved') {
    if (!form.proposal_classification) {
      message.value = '提案判定を選択してください'
      return
    }
  }
  if (isCommitteeStage.value) {
    if (form.term === '' || form.term === null) {
      message.value = '期を入力してください'
      return
    }
    if (form.quarter === '' || form.quarter === null) {
      message.value = '四半期を入力してください'
      return
    }
    const quarterNum = Number(form.quarter)
    if (![1, 2, 3, 4].includes(quarterNum)) {
      message.value = '四半期は1〜4で入力してください'
      return
    }
    if (!form.committee_classification) {
      message.value = '提案判定を選択してください'
      return
    }
  }
  const payload = {
    stage: selectedStage.value,
    status: form.status,
    comment: form.comment,
    confirmed_name: form.confirmed_name,
  }
  if (isManagerStage.value) {
    payload.proposal_classification = form.proposal_classification
    payload.sdgs_flag = form.sdgs_flag
    payload.safety_flag = form.safety_flag
  }
  if (isCommitteeStage.value) {
    payload.term = Number(form.term)
    payload.quarter = Number(form.quarter)
    payload.committee_classification = form.committee_classification
  }
  if (needsScore(selectedStage.value)) {
    payload.scores = {
      mindset: form.mindset,
      idea: form.idea,
      hint: form.hint,
    }
  }
  try {
    await approveProposal(selectedProposal.value.id, payload)
    message.value = '承認を登録しました'
    dialogOpen.value = false
    selectedProposal.value = null
    await loadProposals()
  } catch (error) {
    message.value = error.message ?? '承認登録に失敗しました'
  }
}

const onProposalClassificationChange = () => {
  classificationTouched.value = true
}

watch(selectedStage, () => {
  if (!ensureStage()) return
  selectedProposal.value = null
  loadProposals()
})

watch(
  () => [form.mindset, form.idea, form.hint],
  () => {
    if (!isManagerStage.value) return
    if (classificationTouched.value) return
    form.proposal_classification = suggestClassification()
  }
)

onMounted(() => {
  ensureStage()
  loadProposals()
})
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>✔️ 承認センター</h2>
        <p>あなたの管理権限での承認待ち提案を処理します。</p>
      </div>
      <div class="stage-tabs">
        <button
          v-for="stage in visibleStages"
          :key="stage.value"
          :class="['tab', { active: selectedStage === stage.value }]"
          @click="selectedStage = stage.value"
        >
          {{ stage.label }}
        </button>
      </div>
    </header>

    <div v-if="message" class="alert" :class="{ error: message.includes('失敗'), success: message.includes('登録') }">
      {{ message }}
    </div>

    <div class="content-layout">
      <div class="proposals-list">
        <div v-if="loading" class="loading">読み込み中...</div>
        <div v-else-if="filteredProposals.length === 0" class="no-data">
          承認待ちの提案がありません
        </div>
        <div
          v-else
          v-for="proposal in filteredProposals"
          :key="proposal.id"
          class="proposal-item"
          :class="{ selected: selectedProposal?.id === proposal.id }"
          @click="selectProposal(proposal)"
        >
          <div class="proposal-item-header">
            <span class="management-no">{{ proposal.management_no }}</span>
            <span class="badge badge-pending">承認待ち</span>
          </div>
          <h3 class="proposal-title">{{ proposal.deployment_item }}</h3>
          <div class="proposal-meta">
            <span>提案者: {{ proposal.proposer_detail?.name || proposal.proposer_name }}</span>
            <span>部署: {{ proposal.department_detail?.name }}</span>
            <span v-if="proposal.reduction_hours">
              削減: {{ proposal.reduction_hours }} Hr/月
            </span>
          </div>
          <div class="proposal-date">提出: {{ formatDate(proposal.submitted_at) }}</div>
        </div>
      </div>

      <div v-if="selectedProposal" class="proposal-detail">
        <div class="detail-header">
          <h2>提案詳細</h2>
          <div class="detail-actions">
            <button @click="openApprovalDialog" class="btn-approve" :disabled="!canActOnCurrentStage">
              承認処理
            </button>
            <button @click="closeDetail" class="btn-back">← 戻る</button>
          </div>
        </div>

        <div class="detail-content">
          <div class="detail-section">
            <h3>基本情報</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>管理No</label>
                <span>{{ selectedProposal.management_no }}</span>
              </div>
              <div class="detail-item">
                <label>提出日時</label>
                <span>{{ formatDate(selectedProposal.submitted_at) }}</span>
              </div>
              <div class="detail-item">
                <label>提案者</label>
                <span>{{ selectedProposal.proposer_detail?.name || selectedProposal.proposer_name }}</span>
              </div>
              <div class="detail-item">
                <label>部署</label>
                <span>{{ selectedProposal.department_detail?.name }}</span>
              </div>
              <div class="detail-item span" v-if="contributorsOf(selectedProposal).length">
                <label>共同提案者</label>
                <ul class="contributors">
                  <li v-for="c in contributorsOf(selectedProposal)" :key="c.key">
                    <span class="contrib-name">{{ c.name }} <small v-if="c.code">({{ c.code }})</small></span>
                    <span class="contrib-meta">
                      <span v-if="c.primary" class="pill">主</span>
                      <span v-if="c.share !== ''">{{ formatShare(c.share) }}%</span>
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>テーマ</h3>
            <p>{{ selectedProposal.deployment_item }}</p>
          </div>

          <div class="detail-section">
            <h3>問題点</h3>
            <p class="text-content">{{ selectedProposal.problem_summary }}</p>
          </div>

          <div class="detail-section">
            <h3>改善案</h3>
            <p class="text-content">{{ selectedProposal.improvement_plan }}</p>
          </div>

          <div v-if="selectedProposal.improvement_result" class="detail-section">
            <h3>改善結果</h3>
            <p class="text-content">{{ selectedProposal.improvement_result }}</p>
          </div>

          <div v-if="selectedProposal.effect_details" class="detail-section">
            <h3>効果内容・効果算出</h3>
            <p class="text-content">{{ selectedProposal.effect_details }}</p>
          </div>

          <div class="detail-section">
            <h3>効果</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>削減時間</label>
                <span>{{ selectedProposal.reduction_hours }} Hr/月</span>
              </div>
              <div class="detail-item">
                <label>効果額</label>
                <span>￥{{ (selectedProposal.effect_amount || 0).toLocaleString() }}円/月</span>
              </div>
              <div class="detail-item" v-if="effectDepartments(selectedProposal)">
                <label>効果部門</label>
                <span>{{ effectDepartments(selectedProposal) }}</span>
              </div>
            </div>
          </div>

          <div v-if="beforeImages.length || afterImages.length" class="detail-section">
            <h3>画像</h3>
            <div class="images-grid">
              <div v-for="image in beforeImages" :key="`before-${image.id || image.path}`" class="image-item">
                <label>改善前</label>
                <img :src="image.url || image.path || image" alt="改善前" />
              </div>
              <div v-for="image in afterImages" :key="`after-${image.id || image.path}`" class="image-item">
                <label>改善後</label>
                <img :src="image.url || image.path || image" alt="改善後" />
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>承認状況</h3>
            <div class="approvals-grid">
              <div class="approval-item">
                <label>班長</label>
                <span :class="['badge', 'badge-' + (selectedProposal.supervisor_status || 'pending')]">
                  {{ selectedProposal.supervisor_status === 'approved' ? '承認' : selectedProposal.supervisor_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('supervisor')" class="approval-info">
                  <small>承認者: {{ stageApproval('supervisor').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('supervisor').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('supervisor').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>係長</label>
                <span :class="['badge', 'badge-' + (selectedProposal.chief_status || 'pending')]">
                  {{ selectedProposal.chief_status === 'approved' ? '承認' : selectedProposal.chief_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('chief')" class="approval-info">
                  <small>承認者: {{ stageApproval('chief').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('chief').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('chief').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>課長/部長</label>
                <span :class="['badge', 'badge-' + (selectedProposal.manager_status || 'pending')]">
                  {{ selectedProposal.manager_status === 'approved' ? '承認' : selectedProposal.manager_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('manager')" class="approval-info">
                  <small>承認者: {{ stageApproval('manager').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('manager').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('manager').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>改善委員</label>
                <span :class="['badge', 'badge-' + (selectedProposal.committee_status || 'pending')]">
                  {{ selectedProposal.committee_status === 'approved' ? '承認' : selectedProposal.committee_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('committee')" class="approval-info">
                  <small>承認者: {{ stageApproval('committee').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('committee').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('committee').comment || 'コメント未入力' }}</small>
                </div>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.term || selectedProposal.quarter" class="detail-section">
            <h3>期・四半期</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>期</label>
                <span>{{ selectedProposal.term || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>四半期</label>
                <span>{{ selectedProposal.quarter ? `第${selectedProposal.quarter}四半期` : '-' }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.mindset_score || selectedProposal.idea_score || selectedProposal.hint_score" class="detail-section">
            <h3>評価基準の結果</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>マインドセット</label>
                <span>{{ selectedProposal.mindset_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>アイデア工夫</label>
                <span>{{ selectedProposal.idea_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>みんなのヒント</label>
                <span>{{ selectedProposal.hint_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>合計ポイント</label>
                <span class="total-points">{{ (selectedProposal.mindset_score || 0) + (selectedProposal.idea_score || 0) + (selectedProposal.hint_score || 0) }}点</span>
              </div>
              <div class="detail-item">
                <label>提案ポイント</label>
                <span v-if="proposalPointShare.share !== null">
                  {{ proposalPointShare.share.toFixed(2) }}点
                  <small class="comment">（総計 {{ proposalPointShare.total }}点 を均等割）</small>
                </span>
                <span v-else>-</span>
              </div>
              <div class="detail-item">
                <label>SDGs</label>
                <span>{{ stageApproval('manager')?.sdgs_flag ? '適用' : '未適用' }}</span>
              </div>
              <div class="detail-item">
                <label>安全</label>
                <span>{{ stageApproval('manager')?.safety_flag ? '適用' : '未適用' }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.proposal_classification || selectedProposal.committee_classification" class="detail-section">
            <h3>提案判定</h3>
            <div class="detail-grid">
              <div v-if="selectedProposal.proposal_classification" class="detail-item">
                <label>部課長判定</label>
                <span class="classification-badge">{{ selectedProposal.proposal_classification }}</span>
              </div>
              <div v-if="selectedProposal.committee_classification" class="detail-item">
                <label>改善委員判定</label>
                <span class="classification-badge">{{ selectedProposal.committee_classification }}</span>
              </div>
              <div class="detail-item">
                <label>ポイント</label>
                <span class="classification-badge">
                  {{
                    selectedProposal.classification_points === 0 || selectedProposal.classification_points
                      ? selectedProposal.classification_points
                      : '-'
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="no-selection">
        <p>提案を選択して詳細を表示してください</p>
      </div>
    </div>

    <!-- 承認ダイアログ -->
    <div v-if="dialogOpen" class="modal-overlay" @click.self="closeDialog">
      <div class="modal">
        <h2>承認処理</h2>
        <p class="modal-subtitle">{{ selectedProposal?.management_no }} - {{ selectedProposal?.deployment_item }}</p>

        <form @submit.prevent="submitApproval" class="approval-form">
          <label>
            結果
            <select v-model="form.status" required>
              <option value="approved">承認</option>
              <option value="rejected">却下</option>
            </select>
          </label>

          <label>
            承認者氏名*
            <input v-model="form.confirmed_name" type="text" required />
          </label>

          <div v-if="isManagerStage" class="scores-section">
            <h3>採点スコア (1-5点)</h3>
            <div class="score-grid">
              <label>
                マインドセット
                <input v-model.number="form.mindset" type="number" min="1" max="5" required />
              </label>
              <label>
                アイデア工夫
                <input v-model.number="form.idea" type="number" min="1" max="5" required />
              </label>
              <label>
                みんなのヒント
                <input v-model.number="form.hint" type="number" min="1" max="5" required />
              </label>
            </div>
          </div>

          <div v-if="isManagerStage">
            <label>
              提案判定*
              <select v-model="form.proposal_classification" @change="onProposalClassificationChange" required disabled>
                <option value="" disabled>選択してください</option>
                <option v-for="opt in classificationOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <p v-if="selectedProposal?.committee_classification" class="classification-note">
              改善委員判定: {{ selectedProposal.committee_classification }}
            </p>
          </div>

          <div v-if="isManagerStage">
            <label>
              ポイント（自動計算）
              <input :value="classificationPoints" type="number" readonly disabled placeholder="-" />
            </label>
            <div class="checkbox-row">
              <label class="checkbox">
                <input v-model="form.sdgs_flag" type="checkbox" />
                <span>SDGs</span>
              </label>
              <label class="checkbox">
                <input v-model="form.safety_flag" type="checkbox" />
                <span>安全</span>
              </label>
            </div>
          </div>

          <div v-if="isCommitteeStage" class="term-quarter-grid">
            <label>
              期*
              <input v-model.number="form.term" type="number" min="0" step="1" required />
            </label>
            <label>
              四半期*
              <input v-model.number="form.quarter" type="number" min="1" max="4" step="1" required />
            </label>
          </div>

          <div v-if="isCommitteeStage">
            <label>
              提案判定（部課長の判定をよく確認して、異なる判定の場合、部課長へ連絡してください）*
              <select v-model="form.committee_classification" required>
                <option value="" disabled>選択してください</option>
                <option v-for="opt in classificationOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <p v-if="selectedProposal?.proposal_classification" class="classification-note">
              部課長判定: {{ selectedProposal.proposal_classification }}
            </p>
          </div>

          <label>
            コメント
            <textarea v-model="form.comment" rows="3"></textarea>
          </label>

          <div class="modal-actions">
            <button type="button" @click="closeDialog" class="btn-cancel">キャンセル</button>
            <button type="submit" class="btn-submit" :disabled="!canActOnCurrentStage">承認を実行</button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.stage-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tab {
  padding: 0.6rem 1.2rem;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.tab:hover {
  background: #f3f4f6;
}

.tab.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.content-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 1.5rem;
  min-height: 600px;
}

.proposals-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow-y: auto;
  max-height: 70vh;
  background: #f9fafb;
}

.loading,
.no-data {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
}

.proposal-item {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.proposal-item:hover {
  background: #f3f4f6;
}

.proposal-item.selected {
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
}

.proposal-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.management-no {
  font-weight: 600;
  color: #3b82f6;
  font-size: 0.9rem;
}

.badge {
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.proposal-title {
  font-size: 1rem;
  margin: 0.5rem 0;
  color: #1f2937;
  font-weight: 600;
}

.proposal-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: #6b7280;
}

.proposal-date {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #9ca3af;
}

.proposal-detail {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  overflow-y: auto;
  max-height: 70vh;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.detail-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-approve {
  padding: 0.6rem 1.2rem;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-approve:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-approve:hover:not(:disabled) {
  background: #059669;
}

.btn-back {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.detail-content {
  padding: 1.5rem;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1.1rem;
  color: #374151;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.detail-section p {
  margin: 0;
  color: #4b5563;
  line-height: 1.6;
}

.text-content {
  white-space: pre-wrap;
}

.contributors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.contrib-name {
  font-weight: 600;
  color: #111827;
}

.contrib-name small {
  color: #6b7280;
}

.contrib-meta {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  margin-left: 0.6rem;
  color: #475569;
  font-size: 0.9rem;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0f172a;
  font-size: 0.8rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.detail-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #6b7280;
}

.detail-item span {
  color: #1f2937;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.image-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.image-item label {
  font-weight: 600;
  color: #374151;
}

.image-item img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.approvals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.approval-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.approval-item label {
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.approval-item .badge {
  text-align: center;
}

.badge-approved {
  background: #d1fae5;
  color: #065f46;
}

.badge-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.approval-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.approval-info small {
  font-size: 0.75rem;
  color: #6b7280;
}

.approval-info small.comment {
  color: #374151;
  font-weight: 500;
  margin-top: 0.3rem;
  white-space: pre-wrap;
  line-height: 1.4;
}

.total-points {
  font-weight: 700;
  color: #3b82f6;
  font-size: 1.1rem;
}

.classification-badge {
  display: inline-block;
  padding: 0.4rem 0.8rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 6px;
  font-weight: 600;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  color: #9ca3af;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert.error {
  background: #fee2e2;
  color: #991b1b;
}

.alert.success {
  background: #d1fae5;
  color: #065f46;
}

/* モーダル */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
}

.modal-subtitle {
  color: #6b7280;
  margin: 0 0 1.5rem 0;
  font-size: 0.9rem;
}

.approval-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.term-quarter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}

.approval-form label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-weight: 600;
}

.approval-form input,
.approval-form select,
.approval-form textarea {
  padding: 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
}

.scores-section {
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

.classification-note {
  margin-top: 0.4rem;
  font-size: 0.9rem;
  color: #6b7280;
}

.scores-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #374151;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 0.6rem 1.2rem;
  background: #e5e7eb;
  color: #1f2937;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #d1d5db;
}

.btn-submit {
  padding: 0.6rem 1.2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-submit:hover:not(:disabled) {
  background: #2563eb;
}

.checkbox-row {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.5rem;
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  margin: 0;
}

.checkbox span {
  font-weight: 600;
  color: #374151;
  user-select: none;
}

@media (max-width: 1024px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .proposal-detail {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
    max-height: 100vh;
    border-radius: 0;
  }

  .score-grid {
    grid-template-columns: 1fr;
  }
}
</style>

