const statusLabels = {
  active: '有效',
  expiring: '即将到期',
  expired: '已到期',
  archived: '已归档',
  pending: '待审批',
  approved: '已批准',
  rejected: '已拒绝',
  borrowed: '借出中',
  returned: '已归还',
  overdue: '逾期未还',
}

export function StatusBadge({ status }) {
  return <span className={`status status-${status}`}>{statusLabels[status] || status}</span>
}
