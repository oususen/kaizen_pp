<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { createProposal, fetchCurrentEmployee, fetchDepartments } from '../api/client'

const departments = ref([])
const contributorOptions = ref([])
const employee = ref(null)
const loading = ref(false)
const message = ref('')
const success = ref('')

const form = reactive({
  department: '',
  affiliation: '',
  proposer_name: '',
  proposer_email: '',
  deployment_item: '',
  problem_summary: '',
  improvement_plan: '',
  improvement_result: '',
  contribution_business: [],
  comment: '',
  reduction_hours: '',
  before_image: null,
  after_image: null,
})

const effectAmount = computed(() => {
  const hours = Number(form.reduction_hours) || 0
  return Math.round(hours * 1700)
})

const loadMaster = async () => {
  try {
    const [deptList, emp] = await Promise.all([
      fetchDepartments(),
      fetchCurrentEmployee(),
    ])
    departments.value = deptList
    contributorOptions.value = deptList
    if (emp) {
      employee.value = emp
      form.proposer_name = emp.name ?? ''
      form.proposer_email = emp.email ?? ''
      form.affiliation = emp.position ?? emp.division ?? ''
      if (emp.department) {
        form.department = emp.department
      }
    }
  } catch (error) {
    message.value = error.message ?? 'マスターデータの取得に失敗しました'
  }
}

const resetForm = () => {
  Object.assign(form, {
    department: employee.value?.department ?? '',
    affiliation: employee.value?.position ?? '',
    proposer_name: employee.value?.name ?? '',
    proposer_email: employee.value?.email ?? '',
    deployment_item: '',
    problem_summary: '',
    improvement_plan: '',
    improvement_result: '',
    contribution_business: [],
    comment: '',
    reduction_hours: '',
    before_image: null,
    after_image: null,
  })
  success.value = ''
  message.value = ''
}

const handleFileChange = (event, field) => {
  const [file] = event.target.files ?? []
  form[field] = file || null
}

const submitProposal = async () => {
  message.value = ''
  success.value = ''
  if (!form.department || !form.proposer_name || !form.deployment_item || !form.problem_summary || !form.improvement_plan) {
    message.value = '必須項目を入力してください'
    return
  }
  loading.value = true
  try {
    await createProposal({
      department: form.department,
      affiliation: form.affiliation,
      proposer_name: form.proposer_name,
      proposer_email: form.proposer_email,
      deployment_item: form.deployment_item,
      problem_summary: form.problem_summary,
      improvement_plan: form.improvement_plan,
      improvement_result: form.improvement_result,
      contribution_business: form.contribution_business.join(', '),
      comment: form.comment,
      reduction_hours: form.reduction_hours,
      before_image: form.before_image,
      after_image: form.after_image,
    })
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
        <p>削減時間を入力すると効果額が自動計算されます。</p>
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
          <option v-for="dept in departments" :key="dept.id" :value="dept.id">
            {{ dept.name }}
          </option>
        </select>
      </label>

      <label>
        所属/担当*
        <input v-model="form.affiliation" type="text" required />
      </label>

      <label>
        提案者*
        <input v-model="form.proposer_name" type="text" required />
      </label>

      <label>
        メールアドレス
        <input v-model="form.proposer_email" type="email" />
      </label>

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
        改善結果
        <textarea v-model="form.improvement_result" rows="3"></textarea>
      </label>

      <label>
        削減時間 (Hr/月)*
        <input v-model.number="form.reduction_hours" type="number" min="0" step="0.5" required />
      </label>

      <label>
        効果部門
        <select v-model="form.contribution_business" multiple>
          <option v-for="dept in contributorOptions" :key="dept.id" :value="dept.name">
            {{ dept.name }}
          </option>
        </select>
        <small>Ctrlキーで複数選択</small>
      </label>

      <label class="span">
        コメント・備考
        <textarea v-model="form.comment" rows="2"></textarea>
      </label>

      <label>
        改善前の写真
        <input type="file" accept="image/*" @change="(event) => handleFileChange(event, 'before_image')" />
      </label>

      <label>
        改善後の写真
        <input type="file" accept="image/*" @change="(event) => handleFileChange(event, 'after_image')" />
      </label>

      <div class="span actions">
        <button type="submit" :disabled="loading">{{ loading ? '送信中…' : '提案を提出' }}</button>
        <button type="button" class="ghost" @click="resetForm">クリア</button>
      </div>
    </form>
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
</style>



