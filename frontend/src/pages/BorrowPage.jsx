import { CheckCircle2, Handshake, Save, ThumbsDown, ThumbsUp, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'

import { api } from '../api/client.js'
import { borrowStatuses } from '../api/options.js'
import { EmptyState } from '../components/EmptyState.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'

const initialForm = {
  license: '',
  borrower: '',
  borrower_department: '',
  purpose: '',
  borrow_date: new Date().toISOString().slice(0, 10),
  expected_return_date: '',
  actual_return_date: '',
  status: 'pending',
  notes: '',
}

export function BorrowPage({ licenses, borrowRecords, reload, notify }) {
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [approvalFilter, setApprovalFilter] = useState('')
  const [approvalModal, setApprovalModal] = useState(null)
  const [approvalForm, setApprovalForm] = useState({ approver: '', approval_notes: '' })

  const availableLicenses = useMemo(
    () => licenses.filter((license) => license.computed_status !== 'expired'),
    [licenses],
  )

  const pendingRecords = useMemo(
    () => borrowRecords.filter((record) => record.computed_status === 'pending'),
    [borrowRecords],
  )

  const filteredRecords = useMemo(() => {
    if (!approvalFilter) return borrowRecords
    return borrowRecords.filter((record) => record.computed_status === approvalFilter)
  }, [borrowRecords, approvalFilter])

  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }))

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form, license: Number(form.license) }
      if (!payload.actual_return_date) {
        payload.actual_return_date = null
      }
      await api.createBorrowRecord(payload)
      setForm(initialForm)
      await reload()
      notify('借用申请已提交，等待保管人审批')
    } catch (error) {
      notify(error.message)
    } finally {
      setSaving(false)
    }
  }

  const markReturned = async (record) => {
    const today = new Date().toISOString().slice(0, 10)
    try {
      await api.updateBorrowRecord(record.id, {
        license: record.license,
        borrower: record.borrower,
        borrower_department: record.borrower_department,
        purpose: record.purpose,
        borrow_date: record.borrow_date,
        expected_return_date: record.expected_return_date,
        actual_return_date: today,
        status: 'returned',
        notes: record.notes,
      })
      await reload()
      notify('已登记归还')
    } catch (error) {
      notify(error.message)
    }
  }

  const openApprovalModal = (record, action) => {
    const keeper = record.license_keeper || ''
    if (!keeper.trim()) {
      notify('该证照未指定保管人，请先在证照信息中设置保管人')
      return
    }
    setApprovalModal({ record, action })
    setApprovalForm({ approver: keeper.trim(), approval_notes: '' })
  }

  const closeApprovalModal = () => {
    setApprovalModal(null)
  }

  const submitApproval = async () => {
    if (!approvalModal) return
    const { record, action } = approvalModal
    try {
      const payload = { approval_notes: approvalForm.approval_notes }
      if (action === 'approve') {
        await api.approveBorrowRecord(record.id, payload)
        notify('已批准借用申请，证照进入借出状态')
      } else {
        await api.rejectBorrowRecord(record.id, payload)
        notify('已拒绝借用申请')
      }
      closeApprovalModal()
      await reload()
    } catch (error) {
      notify(error.message)
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Borrowing</p>
          <h1>证照借出归还记录</h1>
        </div>
      </div>

      {pendingRecords.length > 0 && (
        <div className="panel">
          <div className="panel-title">
            <Handshake size={18} />
            <h2>待审批申请 ({pendingRecords.length})</h2>
          </div>
          <div className="data-table">
            <div className="table-head borrow-row">
              <span>证照</span>
              <span>借用人</span>
              <span>保管人</span>
              <span>状态</span>
              <span>操作</span>
            </div>
            {pendingRecords.map((record) => (
              <div className="table-row borrow-row" key={record.id}>
                <div>
                  <strong>{record.license_name}</strong>
                  <span>{record.purpose}</span>
                </div>
                <span>{record.borrower}</span>
                <span>{record.license_keeper || '未指定'}</span>
                <StatusBadge status={record.computed_status} />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => openApprovalModal(record, 'approve')}
                    title="批准"
                  >
                    <ThumbsUp size={16} />
                    <span>批准</span>
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => openApprovalModal(record, 'reject')}
                    title="拒绝"
                    style={{ color: '#dc2626', background: '#fef2f2' }}
                  >
                    <ThumbsDown size={16} />
                    <span>拒绝</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="content-grid form-and-table">
        <form className="panel form-panel" onSubmit={submit}>
          <div className="panel-title">
            <Handshake size={18} />
            <h2>申请借用</h2>
          </div>
          <div className="form-grid">
            <label className="field full">
              <span>证照（已过期证照不可借用）</span>
              <select value={form.license} onChange={(event) => setField('license', event.target.value)} required>
                <option value="">选择证照</option>
                {availableLicenses.map((license) => (
                  <option key={license.id} value={license.id}>
                    {license.name} / {license.license_no}
                    {license.computed_status !== 'active' ? ` (${license.status_display || license.computed_status})` : ''}
                  </option>
                ))}
              </select>
              {licenses.length > availableLicenses.length && (
                <span className="muted" style={{ fontSize: '12px', marginTop: '4px' }}>
                  已过滤 {licenses.length - availableLicenses.length} 个过期证照
                </span>
              )}
            </label>
            <Field label="借用人" value={form.borrower} onChange={(value) => setField('borrower', value)} required />
            <Field label="借用部门" value={form.borrower_department} onChange={(value) => setField('borrower_department', value)} required />
            <Field label="借出日期" type="date" value={form.borrow_date} onChange={(value) => setField('borrow_date', value)} required />
            <Field label="预计归还" type="date" value={form.expected_return_date} onChange={(value) => setField('expected_return_date', value)} required />
            <Field label="用途" value={form.purpose} onChange={(value) => setField('purpose', value)} required />
            <label className="field full">
              <span>备注</span>
              <textarea value={form.notes} onChange={(event) => setField('notes', event.target.value)} />
            </label>
          </div>
          <button className="primary-button" disabled={saving} type="submit">
            <Save size={17} />
            <span>{saving ? '提交中' : '提交申请（待审批）'}</span>
          </button>
        </form>

        <div className="panel table-panel">
          <div className="table-toolbar">
            <select value={approvalFilter} onChange={(event) => setApprovalFilter(event.target.value)}>
              <option value="">全部状态</option>
              {borrowStatuses.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          {filteredRecords.length ? (
            <div className="data-table">
              <div className="table-head borrow-row">
                <span>证照</span>
                <span>借用人</span>
                <span>预计归还</span>
                <span>状态</span>
                <span>操作</span>
              </div>
              {filteredRecords.map((record) => (
                <div className="table-row borrow-row" key={record.id}>
                  <div>
                    <strong>{record.license_name}</strong>
                    <span>{record.purpose}</span>
                    {record.approver && (
                      <span className="muted" style={{ fontSize: '12px' }}>
                        审批人：{record.approver}
                      </span>
                    )}
                  </div>
                  <span>{record.borrower}</span>
                  <span>{record.expected_return_date}</span>
                  <StatusBadge status={record.computed_status} />
                  {record.computed_status === 'returned' ? (
                    <span className="muted">{record.actual_return_date}</span>
                  ) : record.computed_status === 'pending' ? (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => openApprovalModal(record, 'approve')}
                        title="批准"
                      >
                        <ThumbsUp size={16} />
                        <span>批准</span>
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => openApprovalModal(record, 'reject')}
                        title="拒绝"
                        style={{ color: '#dc2626', background: '#fef2f2' }}
                      >
                        <ThumbsDown size={16} />
                        <span>拒绝</span>
                      </button>
                    </div>
                  ) : record.computed_status === 'rejected' ? (
                    <span className="muted">已拒绝</span>
                  ) : (
                    <button className="ghost-button" type="button" onClick={() => markReturned(record)} title="登记归还">
                      <CheckCircle2 size={16} />
                      <span>归还</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无借还记录" description="借出证照后会在这里跟踪归还状态。" />
          )}
        </div>
      </div>

      {approvalModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 50,
          }}
          onClick={closeApprovalModal}
        >
          <div
            className="panel"
            style={{ width: 'min(440px, 92vw)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-title">
              {approvalModal.action === 'approve' ? <ThumbsUp size={18} /> : <ThumbsDown size={18} />}
              <h2>{approvalModal.action === 'approve' ? '批准借用申请' : '拒绝借用申请'}</h2>
              <button
                className="icon-button"
                type="button"
                onClick={closeApprovalModal}
                style={{ marginLeft: 'auto', width: '32px', height: '32px' }}
              >
                <XCircle size={16} />
              </button>
            </div>
            <div style={{ marginBottom: '14px', padding: '10px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <div><strong>{approvalModal.record.license_name}</strong></div>
              <div className="muted" style={{ fontSize: '13px' }}>
                借用人：{approvalModal.record.borrower} · 用途：{approvalModal.record.purpose}
              </div>
            </div>
            <div className="form-grid">
              <label className="field full">
                <span>审批人（保管人，不可修改）</span>
                <input
                  type="text"
                  value={approvalForm.approver}
                  disabled
                  style={{ background: '#f1f5f9', color: '#475569', cursor: 'not-allowed' }}
                />
              </label>
              <label className="field full">
                <span>审批备注</span>
                <textarea
                  value={approvalForm.approval_notes}
                  onChange={(event) => setApprovalForm((cur) => ({ ...cur, approval_notes: event.target.value }))}
                />
              </label>
            </div>
            <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
              <button
                className="ghost-button"
                type="button"
                onClick={closeApprovalModal}
                style={{ flex: 1 }}
              >
                取消
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={submitApproval}
                style={{
                  flex: 1,
                  marginTop: 0,
                  background: approvalModal.action === 'approve' ? '#16a34a' : '#dc2626',
                }}
              >
                {approvalModal.action === 'approve' ? '确认批准' : '确认拒绝'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function Field({ label, value, onChange, type = 'text', required = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  )
}
