import type { Thread } from "@/types/chat";

type SidebarProps = {
  threads:    Thread[];
  activeId:   string;
  onSelect:   (id: string) => void;
  onNew:      () => void;
  onDelete:   (id: string) => void;
  collapsed:  boolean;
  onToggle:   () => void;
};

export function Sidebar({
  threads, activeId, onSelect, onNew, onDelete, collapsed, onToggle,
}: SidebarProps) {
  return (
    <aside className={`shrink-0 flex flex-col bg-gray-50 h-screen transition-all duration-200 ${collapsed ? "w-12" : "w-60"}`}>
      <div className="p-2 flex items-center gap-2">
        <button
          onClick={onToggle}
          className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-200 transition-colors shrink-0"
          title={collapsed ? "展开" : "收起"}
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        {!collapsed && (
          <button
            onClick={onNew}
            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            新建对话
          </button>
        )}
      </div>

      {collapsed ? (
        <div className="flex flex-col items-center pt-1">
          <button
            onClick={onNew}
            className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            title="新建对话"
          >
            <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>
      ) : (
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {threads.length === 0 && (
            <p className="text-xs text-gray-400 text-center mt-6">暂无对话记录</p>
          )}
          {threads.map((t) => (
            <div
              key={t.id}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                t.id === activeId
                  ? "bg-white shadow-sm text-gray-900"
                  : "text-gray-600 hover:bg-white hover:text-gray-900"
              }`}
              onClick={() => onSelect(t.id)}
            >
              <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 shrink-0 text-gray-400" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
              <span className="flex-1 text-sm truncate">{t.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(t.id); }}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-0.5 rounded"
                title="删除"
              >
                <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14H6L5 6" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                  <path d="M9 6V4h6v2" />
                </svg>
              </button>
            </div>
          ))}
        </nav>
      )}
    </aside>
  );
}
