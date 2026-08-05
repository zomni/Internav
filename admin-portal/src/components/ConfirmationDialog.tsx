import { Modal } from './Modal';

interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  danger,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      <p>{message}</p>
      <div className="dialog-actions">
        <button className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
