"use client";

import { createContext, useContext, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

const PanelActive = createContext(true);
export function usePanelActive() { return useContext(PanelActive); }

/** Keep visited panels mounted so switching tabs does not discard form drafts. */
export function SectionTabs({ label, items }: {
  label: string;
  items: { id: string; label: string; content: ReactNode }[];
}) {
  const prefix = useId();
  const [active, setActive] = useState(items[0].id);
  const [visited, setVisited] = useState(() => new Set([items[0].id]));
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  function select(index: number) {
    const id = items[index].id;
    setActive(id);
    setVisited((current) => new Set([...current, id]));
    buttons.current[index]?.focus();
  }

  return (
    <div className="section-tabs full-span">
      <div className="section-tab-list" role="tablist" aria-label={label}>
        {items.map((item, index) => (
          <button key={item.id} type="button" role="tab"
            id={`${prefix}-tab-${item.id}`} aria-controls={`${prefix}-panel-${item.id}`}
            aria-selected={active === item.id} tabIndex={active === item.id ? 0 : -1}
            ref={(element) => { buttons.current[index] = element; }}
            onClick={() => select(index)}
            onKeyDown={(event) => {
              let next: number;
              if (event.key === "ArrowRight") next = (index + 1) % items.length;
              else if (event.key === "ArrowLeft") next = (index + items.length - 1) % items.length;
              else if (event.key === "Home") next = 0;
              else if (event.key === "End") next = items.length - 1;
              else return;
              event.preventDefault();
              select(next);
            }}>
            {item.label}
          </button>
        ))}
      </div>
      {items.map((item) => (
        <div key={item.id} role="tabpanel" id={`${prefix}-panel-${item.id}`}
          aria-labelledby={`${prefix}-tab-${item.id}`} hidden={active !== item.id} tabIndex={0}>
          <PanelActive.Provider value={active === item.id}>{visited.has(item.id) ? item.content : null}</PanelActive.Provider>
        </div>
      ))}
    </div>
  );
}
