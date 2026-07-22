import Modal from "./Modal";

export default function ConfirmDialog({ title = "Confirm", message, onConfirm, onCancel }) {
  return (
    <Modal title={title} onClose={onCancel}>
      <p className="text-sm text-foreground/80 mb-5">{message}</p>
      <div className="flex gap-3">
        <button
          onClick={onCancel}
          className="flex-1 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="flex-1 bg-red-600 hover:bg-red-500 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Delete
        </button>
      </div>
    </Modal>
  );
}
