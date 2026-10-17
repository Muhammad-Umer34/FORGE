// D:\FYP\FORGE-1\frontend\src\components\clarification\ThemePicker.tsx
"use client";

import { useEffect } from "react";
import { ThemeCard } from "@/types/request";

/** Load each theme's Google Fonts once, so the preview shows the real typefaces. */
function useGoogleFonts(families: string[]) {
  const key = [...new Set(families)].sort().join("|");
  useEffect(() => {
    key.split("|").filter(Boolean).forEach((family) => {
      const id = `gf-${family.replace(/\s+/g, "-").toLowerCase()}`;
      if (document.getElementById(id)) return;
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family).replace(/%20/g, "+")}&display=swap`;
      document.head.appendChild(link);
    });
  }, [key]);
}

interface ThemePickerProps {
  themes: ThemeCard[];
  selected: string;
  onSelect: (id: string) => void;
  disabled: boolean;
}

export function ThemePicker({ themes, selected, onSelect, disabled }: ThemePickerProps) {
  useGoogleFonts(themes.flatMap((t) => [t.fonts.heading, t.fonts.body]));

  return (
    <div role="radiogroup" aria-label="Look and feel" className="grid gap-3 sm:grid-cols-3">
      {themes.map((theme) => {
        const on = theme.id === selected;
        const s = theme.swatch[theme.default_mode];
        // Theme values are data from the API, so they are passed as CSS variables, not hardcoded classes.
        const vars = {
          "--t-bg": s.background,
          "--t-card": s.card,
          "--t-fg": s.foreground,
          "--t-muted": s.muted,
          "--t-primary": s.primary,
          "--t-on-primary": s["primary-foreground"],
          "--t-accent": s.accent,
          "--t-radius": theme.radius,
          "--t-heading": `"${theme.fonts.heading}", serif`,
          "--t-body": `"${theme.fonts.body}", sans-serif`,
        } as React.CSSProperties;
        return (
          <button
            key={theme.id}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={`${theme.label}. ${theme.reason}. Fonts: ${theme.fonts.heading} and ${theme.fonts.body}.`}
            disabled={disabled}
            onClick={() => onSelect(theme.id)}
            className={`group rounded-xl border p-2 text-left transition-all duration-200 active:scale-[0.99] ${
              on ? "border-ember ring-2 ring-ember/30" : "border-line hover:border-ink-faint"
            }`}
          >
            <span
              aria-hidden="true"
              style={vars}
              className="block overflow-hidden rounded-lg bg-[var(--t-bg)] p-3.5 [font-family:var(--t-body)]"
            >
              <span className="block text-[17px] leading-tight text-[var(--t-fg)] [font-family:var(--t-heading)]">
                Welcome to our site
              </span>
              <span className="mt-1.5 block h-1.5 w-4/5 rounded-full bg-[var(--t-muted)]" />
              <span className="mt-1 block h-1.5 w-3/5 rounded-full bg-[var(--t-muted)]" />
              <span className="mt-3 flex items-center gap-2">
                <span className="rounded-[var(--t-radius)] bg-[var(--t-primary)] px-2.5 py-1 text-[11px] font-medium text-[var(--t-on-primary)]">
                  Contact us
                </span>
                <span className="h-5 w-5 rounded-[var(--t-radius)] bg-[var(--t-accent)]" />
                <span className="h-5 flex-1 rounded-[var(--t-radius)] bg-[var(--t-card)]" />
              </span>
            </span>
            <span className="mt-2.5 flex items-start justify-between gap-2 px-1">
              <span>
                <span className="block text-[15px] font-medium text-ink">{theme.label}</span>
                <span className="block text-[12px] text-ink-muted">{theme.reason}</span>
                <span className="mt-0.5 block text-[12px] text-ink-faint">
                  {theme.fonts.heading === theme.fonts.body ? theme.fonts.heading : `${theme.fonts.heading} + ${theme.fonts.body}`}
                </span>
              </span>
              <span className="flex flex-col items-end gap-0.5">
                {on && <span className="mt-0.5 text-[12px] font-medium text-ember-strong">Selected</span>}
                {theme.default_mode === "dark" && <span className="text-[11px] text-ink-faint">Dark</span>}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
