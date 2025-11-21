import { computed } from 'vue'
import { useAuth } from '../stores/auth'

export function usePermissions() {
  const auth = useAuth()

  const canView = (resource) => {
    return auth.canView(resource)
  }

  const canEdit = (resource) => {
    return auth.canEdit(resource)
  }

  // ページごとの権限チェック
  const permissions = computed(() => ({
    submit: {
      canView: canView('submit'),
      canEdit: canEdit('submit'),
    },
    proposals: {
      canView: canView('proposals'),
      canEdit: canEdit('proposals'),
    },
    approvals: {
      canView: canView('approvals'),
      canEdit: canEdit('approvals'),
    },
    confirmed: {
      canView: canView('confirmed'),
      canEdit: canEdit('confirmed'),
    },
    reports: {
      canView: canView('reports'),
      canEdit: canEdit('reports'),
    },
    analytics: {
      canView: canView('analytics'),
      canEdit: canEdit('analytics'),
    },
    permissions: {
      canView: canView('permissions'),
      canEdit: canEdit('permissions'),
    },
  }))

  return {
    canView,
    canEdit,
    permissions,
  }
}
