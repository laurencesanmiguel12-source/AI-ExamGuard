import { Clock } from "lucide-react";
import Modal from "./Modal";

export default function IdleLogoutWarningModal({ onStayLoggedIn, onLogoutNow }) {
  return (
    <Modal title="Still There?" onClose={onStayLoggedIn}>
      <div className="flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mb-4">
          <Clock className="w-7 h-7 text-amber-700" />
        </div>
        <p className="text-sm text-foreground/80 mb-5">
          You've been inactive for a while. For your security, you'll be logged out in about a
          minute unless you stay active.
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={onLogoutNow}
          className="flex-1 border border-border hover:border-foreground/20 text-muted-foreground hover:text-foreground py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Log Out Now
        </button>
        <button
          onClick={onStayLoggedIn}
          className="flex-1 bg-primary hover:bg-primary/90 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
        >
          Stay Logged In
        </button>
      </div>
    </Modal>
  );
}
