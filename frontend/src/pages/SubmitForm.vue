<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { createProposal, fetchDepartments, fetchEmployees } from '../api/client'

const departments = ref([])
const employees = ref([])
const loading = ref(false)
const message = ref('')
const success = ref('')
const primaryContributor = reactive({ code: '', employee: null })
const coContributors = ref([])
const showLookup = ref(false)
const lookupKeyword = ref('')
const lookupResults = ref([])
const lookupTarget = ref(null)
const lookupLoading = ref(false)
const lookupMessage = ref('')

const form = reactive({
  department: '',
  group: '',
  team: '',
  proposer: '',
  proposer_name: '',
  proposer_email: '',
  deployment_item: '',
  problem_summary: '',
  improvement_plan: '',
  improvement_result: '',
  effect_details: '',
  contribution_business: [],
  reduction_hours: null,
  effect_amount: null,
  before_images: [],
  after_images: [],
})

const toId = (value) => (value === null || value === undefined ? '' : String(value))

const parentMap = computed(() => {
  const map = new Map()
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), toId(dept.parent))
  })
  return map
})

const isDescendantOf = (childId, ancestorId) => {
  let cursor = toId(childId)
  const target = toId(ancestorId)
  if (!cursor || !target) return false
  const seen = new Set()
  while (cursor && !seen.has(cursor)) {
    seen.add(cursor)
    const parent = parentMap.value.get(cursor)
    if (!parent) return false
    if (parent === target) return true
    cursor = parent
  }
  return false
}

const divisionOptions = computed(() => departments.value.filter((dept) => dept.level === 'division'))
const groupOptions = computed(() => departments.value.filter((dept) => dept.level === 'group'))
const teamOptions = computed(() => departments.value.filter((dept) => dept.level === 'team'))
const filteredGroupOptions = computed(() =>
  groupOptions.value.filter((dept) => isDescendantOf(dept.id, form.department)),
)
const filteredTeamOptions = computed(() =>
  teamOptions.value.filter((dept) => isDescendantOf(dept.id, form.group)),
)
const effectDepartmentOptions = computed(() => 
  departments.value
    .filter((dept) => dept.level === 'division' || dept.level === 'section')
    .sort((a, b) => {
      // Sort by display_id first, then by name
      const idDiff = (a.display_id || 0) - (b.display_id || 0)
      if (idDiff !== 0) return idDiff
      return a.name.localeCompare(b.name)
    })
)

const effectAmount = computed(() => {
  // 優先: 手入力の月間効果額、未入力なら削減時間×1700で自動計算
  const manual = Number(form.effect_amount)
  if (!Number.isNaN(manual) && form.effect_amount !== null && form.effect_amount !== '') {
    return manual
  }
  const hours = Number(form.reduction_hours) || 0
  return Math.round(hours * 1700)
})

const hasReductionHours = computed(
  () => form.reduction_hours !== null && form.reduction_hours !== '' && !Number.isNaN(Number(form.reduction_hours)),
)
const hasEffectAmount = computed(
  () => form.effect_amount !== null && form.effect_amount !== '' && !Number.isNaN(Number(form.effect_amount)),
)

const loadMaster = async () => {
  try {
    departments.value = await fetchDepartments()
  } catch (error) {
    message.value = error.message ?? 'マスターデータの取得に失敗しました'
  }
}


const loadEmployees = async (departmentId = null) => {
  try {
    const params = departmentId ? { department: departmentId } : {}
    employees.value = await fetchEmployees(params)
  } catch (error) {
    message.value = error.message ?? '社員データの取得に失敗しました'
  }
}

const resetForm = () => {
  Object.assign(form, {
    department: '',
    group: '',
    team: '',
    proposer: '',
    proposer_name: '',
    proposer_email: '',
    deployment_item: '',
    problem_summary: '',
    improvement_plan: '',
    improvement_result: '',
    effect_details: '',
    contribution_business: [],
    reduction_hours: null,
    effect_amount: null,
    before_images: [],
    after_images: [],
  })
  primaryContributor.code = ''
  primaryContributor.employee = null
  coContributors.value = []
  success.value = ''
  message.value = ''
}


// 提案者選択時に名前とメールアドレスを自動入力
// 部署・主提案者の選択
watch(() => form.department, (newDepartment) => {
  if (!filteredGroupOptions.value.some((dept) => toId(dept.id) === toId(form.group))) {
    form.group = ''
  }
  form.team = ''
  form.proposer = ''
  primaryContributor.code = ''
  primaryContributor.employee = null
  coContributors.value = []
  if (newDepartment) {
    loadEmployees(newDepartment)
  } else {
    employees.value = []
  }
})

watch(() => form.group, (newGroup) => {
  if (!filteredTeamOptions.value.some((dept) => toId(dept.id) === toId(form.team))) {
    form.team = ''
  }
  form.proposer = ''
  if (newGroup) {
    loadEmployees(newGroup)
  } else if (form.department) {
    loadEmployees(form.department)
  }
})

watch(() => form.team, (newTeam) => {
  form.proposer = ''
  if (newTeam) {
    loadEmployees(newTeam)
  } else if (form.group) {
    loadEmployees(form.group)
  } else if (form.department) {
    loadEmployees(form.department)
  }
})

watch(() => form.proposer, (proposerId) => {
  const employee = employees.value.find(emp => String(emp.id) === String(proposerId))
  if (employee) {
    form.proposer_name = employee.name
    form.proposer_email = employee.email || ''
    primaryContributor.code = employee.code || ''
    primaryContributor.employee = employee
  } else {
    form.proposer_name = ''
    form.proposer_email = ''
    primaryContributor.code = ''
    primaryContributor.employee = null
  }
})

const addCoContributor = () => {
  coContributors.value.push({ code: '', employee: null })
}

const removeCoContributor = (index) => {
  coContributors.value.splice(index, 1)
}

const searchByCode = async (target) => {
  if (!target) return
  if (!target.code) {
    target.employee = null
    return
  }
  try {
    const raw = String(target.code).trim()
    const padded = raw.padStart(6, '0')
    let results = await fetchEmployees({ code: padded })
    if (!Array.isArray(results) || results.length === 0) {
      results = await fetchEmployees({ q: raw })
    }
    const found = Array.isArray(results) ? results[0] : null
    target.employee = found || null
    if (found?.code) {
      target.code = found.code
    }
    if (!found) {
      message.value = '該当する社員が見つかりません'
    }
  } catch (error) {
    message.value = error.message ?? '社員検索に失敗しました'
  }
}

const openLookup = (target) => {
  lookupTarget.value = target
  lookupKeyword.value = ''
  lookupResults.value = []
  lookupMessage.value = ''
  showLookup.value = true
  runLookup()
}

const closeLookup = () => {
  showLookup.value = false
}

const runLookup = async () => {
  lookupLoading.value = true
  lookupMessage.value = ''
  lookupResults.value = []
  try {
    const keyword = (lookupKeyword.value || '').trim()
    const params = {}
    if (form.department) params.department = form.department

    console.log('[SubmitForm] Employee search - keyword:', keyword, 'params:', params)

    const tryResults = []

    // 優先: 数字ならゼロ埋めコード検索
    if (keyword && /^\d+$/.test(keyword)) {
      const padded = keyword.padStart(6, '0')
      console.log('[SubmitForm] Searching by code:', padded)
      const codeResults = await fetchEmployees({ ...params, code: padded })
      console.log('[SubmitForm] Code search results:', codeResults)
      tryResults.push(codeResults)
    }

    // q検索
    console.log('[SubmitForm] Searching by keyword')
    const qResults = await fetchEmployees(keyword ? { ...params, q: keyword } : params)
    console.log('[SubmitForm] Keyword search results:', qResults)
    tryResults.push(qResults)

    // 何もヒットしなければ全件（部署絞り込みのみ）を表示
    const firstHit = tryResults.find((arr) => Array.isArray(arr) && arr.length)
    if (firstHit && firstHit.length) {
      lookupResults.value = firstHit
      console.log('[SubmitForm] Found results:', lookupResults.value.length)
    } else {
      console.log('[SubmitForm] No hits, fetching all employees for department')
      lookupResults.value = await fetchEmployees(params)
      console.log('[SubmitForm] All employees results:', lookupResults.value.length)
    }

    if (!lookupResults.value.length) {
      lookupMessage.value = '該当する社員が見つかりません'
    }
  } catch (error) {
    console.error('[SubmitForm] Employee search error:', error)
    lookupMessage.value = error.message ?? '社員検索に失敗しました'
  } finally {
    lookupLoading.value = false
  }
}

const applyLookup = (employee) => {
  const target = lookupTarget.value
  if (target === 'primary') {
    primaryContributor.code = employee.code || ''
    primaryContributor.employee = employee
    form.proposer = toId(employee.id)
    form.proposer_name = employee.name
    form.proposer_email = employee.email || ''
  } else if (typeof target === 'number') {
    const entry = coContributors.value[target]
    if (entry) {
      entry.code = employee.code || ''
      entry.employee = employee
    }
  }
  closeLookup()
}

// モーダルを開いたら一覧を事前取得
watch(showLookup, (visible) => {
  if (visible) {
    runLookup()
  }
})

const handleFilesChange = (event, field) => {
  const files = Array.from(event.target.files || [])
  form[field] = files
}

const removeImage = (field, index) => {
  form[field].splice(index, 1)
}

const getImagePreviewUrl = (file) => {
  try {
    if (file instanceof File || file instanceof Blob) {
      return URL.createObjectURL(file)
    }
    return ''
  } catch (error) {
    console.error('Failed to create object URL:', error)
    return ''
  }
}

const submitProposal = async () => {
  message.value = ''
  success.value = ''
  const requiredFields = [
    form.department,
    form.deployment_item,
    form.problem_summary,
    form.improvement_plan,
    form.improvement_result,
    form.effect_details,
  ]
  const hasEmptyRequired = requiredFields.some(
    (value) => value === null || value === undefined || (typeof value === 'string' && value.trim() === ''),
  )
  if (hasEmptyRequired || form.contribution_business.length === 0 || !primaryContributor.employee) {
    message.value = '必須項目を入力してください'
    return
  }
  if (!hasReductionHours.value && !hasEffectAmount.value) {
    message.value = '削減時間 または 月間効果額を入力してください'
    return
  }
  loading.value = true
  try {
    if (primaryContributor.employee) {
      form.proposer = primaryContributor.employee.id
      form.proposer_name = primaryContributor.employee.name
      form.proposer_email = primaryContributor.employee.email || ''
    }
    const contributors = []
    if (primaryContributor.employee) {
      contributors.push({ employee: primaryContributor.employee.id, is_primary: true })
    }
    coContributors.value.forEach((contrib) => {
      if (contrib.employee) {
        contributors.push({ employee: contrib.employee.id, is_primary: false })
      }
    })
    console.log('[SubmitForm] Contributors being sent:', contributors)
    console.log('[SubmitForm] Primary contributor:', primaryContributor)
    console.log('[SubmitForm] Co-contributors:', coContributors.value)
    // FormDataを使って複数画像を送信
    const formData = {
      department: form.department,
      group: form.group,
      team: form.team,
      proposer: form.proposer,
      proposer_name: form.proposer_name,
      proposer_email: form.proposer_email,
      deployment_item: form.deployment_item,
      problem_summary: form.problem_summary,
      improvement_plan: form.improvement_plan,
      improvement_result: form.improvement_result,
      effect_details: form.effect_details,
      contribution_business: form.contribution_business.join(', '),
      reduction_hours: form.reduction_hours,
      effect_amount: form.effect_amount,
      before_images: form.before_images,
      after_images: form.after_images,
      contributors,
    }
    await createProposal(formData)
    success.value = '改善提案を提出しました'
    resetForm()
  } catch (error) {
    message.value = error.message ?? '送信に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMaster()
})
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>📝 改善提案 提出フォーム</h2>
        <p>削減時間を入力すると効果額が自動計算されます。月間金額を直接入力することもできます。</p>
      </div>
      <div class="effect">
        <span>月間効果額</span>
        <strong>¥{{ effectAmount.toLocaleString() }}</strong>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="success" class="alert success">{{ success }}</div>

    <form class="form-grid" @submit.prevent="submitProposal">
      <label>
        部門*
        <select v-model="form.department" required>
          <option value="" disabled>選択してください</option>
          <option v-for="dept in divisionOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>

      <label>
        係
        <select v-model="form.group">
          <option value="">選択してください</option>
          <option v-for="dept in filteredGroupOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>

      <label>
        班
        <select v-model="form.team">
          <option value="">選択してください</option>
          <option v-for="dept in filteredTeamOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>


      <label>
        提案者*
        <select v-model="form.proposer" required>
          <option value="" disabled>選択してください</option>
          <option v-for="emp in employees" :key="emp.id" :value="toId(emp.id)">
            {{ emp.name }} ({{ emp.code }})
          </option>
        </select>
      </label>

      <label>
        提案者名
        <input v-model="form.proposer_name" type="text" readonly />
      </label>

      <div class="span contributor-section">
        <div class="co-header">
          <span>共同提案者（任意・社員番号）</span>
          <div class="contributor-actions">
            <button type="button" class="ghost" @click="openLookup('primary')">主提案者を検索</button>
            <button type="button" class="ghost" @click="addCoContributor">共同者を追加</button>
          </div>
        </div>
        <div v-if="!coContributors.length" class="helper-text">必要に応じて追加してください</div>
        <div v-for="(contrib, index) in coContributors" :key="index" class="contributor-row co-row">
          <input
            v-model="contrib.code"
            type="text"
            inputmode="numeric"
            placeholder="社員番号を入力"
            @blur="searchByCode(contrib)"
          />
          <span class="contributor-name">{{ contrib.employee?.name || '未選択' }}</span>
          <div class="contributor-actions">
            <button type="button" class="ghost" @click="openLookup(index)">検索</button>
            <button type="button" class="remove-btn small" @click="removeCoContributor(index)">×</button>
          </div>
        </div>
      </div>

      <label class="span">
        展開項目(テーマ)*
        <input v-model="form.deployment_item" type="text" required />
      </label>

      <label class="span">
        困っている事・問題点*
        <textarea v-model="form.problem_summary" rows="3" required></textarea>
      </label>

      <label class="span">
        この様に改善したい*
        <textarea v-model="form.improvement_plan" rows="3" required></textarea>
      </label>

      <label class="span">
        改善結果*
        <textarea v-model="form.improvement_result" rows="3" required></textarea>
      </label>

      <label class="span">
        効果内容・効果算出*
        <textarea
          v-model="form.effect_details"
          rows="3"
          placeholder="時間単価１７００円で計算すること。削減時間は「誰が」「どれだけ」がわかるように記入してください。"
          required
        ></textarea>
        <small style="color: #64748b; font-style: italic;">
          ※時間単価１７００円で計算すること。削減時間は「誰が」「どれだけ」がわかるように記入してください。
        </small>
      </label>

      <label>
        削減時間 (Hr/月)
        <input
          v-model.number="form.reduction_hours"
          type="number"
          min="0"
          step="0.01"
          :readonly="hasEffectAmount"
        />
        <small style="color: #64748b;">この欄に値があると月間効果額を自動計算し、金額欄は入力不可になります。</small>
      </label>

      <label>
        月間効果額 (円/月)
        <input
          :value="hasReductionHours ? effectAmount : form.effect_amount"
          @input="form.effect_amount = $event.target.value === '' ? null : Number($event.target.value)"
          type="number"
          min="0"
          step="1"
          inputmode="numeric"
          :readonly="hasReductionHours"
        />
        <small style="color: #64748b;">
          この欄に値があると時間欄は入力不可になります。削減時間を入れるとここに自動計算(×1700)が表示されます。
        </small>
      </label>

      <label>
        効果部門*
        <select v-model="form.contribution_business" multiple required>
          <option v-for="dept in effectDepartmentOptions" :key="dept.id" :value="dept.name">
            {{ dept.name }}
          </option>
        </select>
        <small>Ctrlキーで複数選択</small>
      </label>

      <div class="image-upload-section span">
        <div class="image-upload-container">
          <div class="image-upload-column">
            <h3>改善前の写真 </h3>
            <!-- <h3>改善前の写真 <span class="required-badge">必須</span></h3> -->
            <input
              type="file"
              accept="image/*"
              multiple
              @change="(event) => handleFilesChange(event, 'before_images')"
              class="file-input"
            />
            <div v-if="form.before_images.length > 0" class="image-preview-grid">
              <div v-for="(file, index) in form.before_images" :key="index" class="image-preview-item">
                <img v-if="getImagePreviewUrl(file)" :src="getImagePreviewUrl(file)" :alt="`改善前 ${index + 1}`" />
                <button type="button" @click="removeImage('before_images', index)" class="remove-btn">×</button>
                <span class="image-name">{{ file.name }}</span>
              </div>
            </div>
            <p v-else class="upload-hint">複数枚選択可能</p>
          </div>

          <div class="image-upload-column">
            <h3>改善後の写真</h3>
            <input
              type="file"
              accept="image/*"
              multiple
              @change="(event) => handleFilesChange(event, 'after_images')"
              class="file-input"
            />
            <div v-if="form.after_images.length > 0" class="image-preview-grid">
              <div v-for="(file, index) in form.after_images" :key="index" class="image-preview-item">
                <img v-if="getImagePreviewUrl(file)" :src="getImagePreviewUrl(file)" :alt="`改善後 ${index + 1}`" />
                <button type="button" @click="removeImage('after_images', index)" class="remove-btn">×</button>
                <span class="image-name">{{ file.name }}</span>
              </div>
            </div>
            <p v-else class="upload-hint">複数枚選択可能</p>
          </div>
        </div>
      </div>

      <div class="span actions">
        <button type="submit" :disabled="loading">{{ loading ? '送信中…' : '提案を提出' }}</button>
        <button type="button" class="ghost" @click="resetForm">クリア</button>
      </div>
    </form>


      <div v-if="showLookup" class="modal-backdrop" @click.self="closeLookup">
        <div class="modal">
          <h3>社員検索</h3>
          <div class="modal-controls">
            <input
              v-model="lookupKeyword"
              type="text"
              placeholder="社員番号・氏名・部署で検索"
              @keyup.enter="runLookup"
            />
            <div class="modal-actions">
              <button type="button" :disabled="lookupLoading" @click="runLookup">
                {{ lookupLoading ? '検索中...' : '検索' }}
              </button>
              <button type="button" class="ghost" @click="closeLookup">閉じる</button>
            </div>
          </div>
          <div v-if="lookupMessage" class="lookup-message error">
            {{ lookupMessage }}
          </div>
          <div v-if="lookupLoading" class="lookup-message info">
            検索中...
          </div>
          <div v-if="!lookupLoading && !lookupMessage && lookupResults.length > 0" class="lookup-message success">
            {{ lookupResults.length }}件の社員が見つかりました
          </div>
          <div class="lookup-list">
            <button
              type="button"
              v-for="emp in lookupResults"
              :key="emp.id"
              class="lookup-item"
              @click="applyLookup(emp)"
            >
              <div>
                <strong>{{ emp.code }}</strong> {{ emp.name }}
              </div>
              <small>{{ emp.department_detail?.name || '部署未設定' }}</small>
            </button>
          </div>
        </div>
      </div>
</section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.effect {
  text-align: right;
  background: #eef2ff;
  padding: 0.7rem 1rem;
  border-radius: 8px;
}
.effect span {
  display: block;
  font-size: 0.8rem;
  color: #4c1d95;
}
.effect strong {
  font-size: 1.3rem;
  color: #1d4ed8;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
label {
  display: flex;
  flex-direction: column;
  font-weight: 600;
  gap: 0.4rem;
}
input,
select,
textarea {
  padding: 0.5rem 0.6rem;
  border: 1px solid #d4dbe5;
  border-radius: 8px;
  font-size: 1rem;
}
textarea {
  resize: vertical;
}
.span {
  grid-column: 1 / -1;
}
.actions {
  display: flex;
  gap: 0.6rem;
}
button {
  padding: 0.7rem 1.4rem;
  border-radius: 8px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}
button.ghost {
  background: #e2e8f0;
  color: #1f2933;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.alert {
  margin: 1rem 0;
  padding: 0.8rem 1rem;
  border-radius: 8px;
}
.alert.error {
  background: #fee2e2;
  color: #991b1b;
}
.alert.success {
  background: #dcfce7;
  color: #166534;
}

.contributor-section {
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.contributor-header,
.co-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.inline-label {
  font-weight: 700;
}
.contributor-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.75rem;
}
.co-row {
  grid-template-columns: 1fr 1fr auto;
}
.contributor-name {
  color: #334155;
  font-weight: 600;
}
.contributor-actions {
  display: flex;
  gap: 0.4rem;
}
.helper-text {
  color: #6b7280;
  font-size: 0.9rem;
}
.lookup-message {
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  text-align: center;
}
.lookup-message.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}
.lookup-message.success {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}
.lookup-message.info {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}
.modal {
  background: #fff;
  padding: 1.5rem;
  border-radius: 12px;
  width: min(600px, 90%);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.modal-controls {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.modal-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.lookup-list {
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.lookup-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
}
.lookup-item:hover {
  border-color: #2563eb;
}
.lookup-item small {
  color: #6b7280;
}
.remove-btn.small {
  width: auto;
  height: auto;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
}

/* 画像アップロードセクション */
.image-upload-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
}

.image-upload-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.image-upload-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.image-upload-column h3 {
  font-size: 1.1rem;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.required-badge {
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.file-input {
  padding: 0.8rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
}

.file-input:hover {
  border-color: #3b82f6;
}

.upload-hint {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0;
  text-align: center;
  font-style: italic;
}

.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.image-preview-item {
  position: relative;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.image-preview-item img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
}

.image-name {
  display: block;
  padding: 0.4rem;
  font-size: 0.75rem;
  color: #64748b;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  padding: 0;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 50%;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  background: #dc2626;
}

.contributor-section {
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.contributor-header,
.co-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.inline-label {
  font-weight: 700;
}
.contributor-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.75rem;
}
.co-row {
  grid-template-columns: 1fr 1fr auto;
}
.contributor-name {
  color: #334155;
  font-weight: 600;
}
.contributor-actions {
  display: flex;
  gap: 0.4rem;
}
.helper-text {
  color: #6b7280;
  font-size: 0.9rem;
}
.remove-btn.small {
  width: auto;
  height: auto;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
}

@media (max-width: 768px) {
  .image-upload-container {
    grid-template-columns: 1fr;
  }
}
</style>






