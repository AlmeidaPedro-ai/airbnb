import type { ReactNode } from "react";

interface ModalProps {
  titulo: string;
  aberto: boolean;
  onClose: () => void;
  children: ReactNode;
  largura?: number;
}

export default function Modal({
  titulo,
  aberto,
  onClose,
  children,
  largura = 560,
}: ModalProps) {
  if (!aberto) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: largura }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3>{titulo}</h3>
          <button className="btn-icone" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
