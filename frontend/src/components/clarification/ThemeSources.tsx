// D:\FYP\FORGE-1\frontend\src\components\clarification\ThemeSources.tsx
"use client";

import { useRef, useState } from "react";
import { ImageColours, ThemeSource, ThemeSourceKind } from "@/types/request";

/**
 * "Use your own style" (theme Phase 2): a logo, a website screenshot, or a website the user likes.
 * Images are read by our backend (local colour maths, no model call, never stored); the user then
 * confirms the colour, and only that colour is sent to the run.
 */
interface ThemeSourcesProps {
  left: Record<ThemeSourceKind, number>;
  notice: string | null;
  busy: boolean;
  onReadImage: (kind: "logo" | "screenshot", file: File) => Promise<ImageColours>;
  onUse: (source: ThemeSource) => void;
}

type Panel = "none" | "logo" | "screenshot" | "website";

const ACCEPT = "image/png,image/jpeg,image/webp";

function Swatch({ colour, label }: { colour: string; label?: string }) {
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true" className="h-7 w-7 rounded-md border border-line bg-[var(--sw)]" style={{ "--sw": colour } as React.CSSProperties} />
      <span className="font-mono text-[12px] text-ink-muted">{label ? `${label} ` : ""}{colour}</span>
    </span>
  );
}

export function ThemeSources({ left, notice, busy, onReadImage, onUse }: ThemeSourcesProps) {
  const [panel, setPanel] = useState<Panel>("none");
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImageColours | null>(null);
  const [url, setUrl] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const disabled = busy || reading;

  const open = (next: Panel) => {
    setPanel(next);
    setError(null);
    setResult(null);
    if (next === "logo" || next === "screenshot") fileInput.current?.click();
  };

  const onFile = async (file: File | undefined) => {
    if (!file || (panel !== "logo" && panel !== "screenshot")) return;
    setReading(true);
    setError(null);
    try {
      setResult(await onReadImage(panel, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't read that image.");
    } finally {
      setReading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const button = (kind: Panel, text: string) => {
    const sourceKind = kind as ThemeSourceKind;
    return (
      <button
        type="button"
        disabled={disabled || !left[sourceKind]}
        aria-pressed={panel === kind}
        onClick={() => open(kind)}
        className={`rounded-lg border px-3.5 py-2 text-[13px] font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
          panel === kind ? "border-ember bg-ember-soft text-ember-strong" : "border-line text-ink hover:border-ink-faint hover:bg-surface"
        }`}
      >
        {text}
      </button>
    );
  };

  return (
    <div className="mt-5 rounded-lg border border-dashed border-line px-4 py-4">
      <p className="text-[13px] font-medium text-ink">Use your own style</p>
      <p className="mt-0.5 text-[12px] text-ink-muted">
        Take colours from your logo, a screenshot, or a website you like. Only colours, fonts and corners are used.
      </p>

      {notice && (
        <p role="status" className="mt-3 rounded-md bg-ember-soft px-3 py-2 text-[13px] text-ember-strong">{notice}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {button("logo", "Use my logo")}
        {button("screenshot", "Upload a website screenshot")}
        {button("website", "Match a website I like")}
      </div>

      <input
        ref={fileInput}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        aria-label={panel === "screenshot" ? "Website screenshot" : "Logo image"}
        onChange={(e) => onFile(e.target.files?.[0])}
      />

      {reading && <p role="status" className="mt-3 text-[13px] text-ink-muted">Reading the colours…</p>}
      {error && <p role="alert" className="mt-3 rounded-md bg-alert-soft px-3 py-2 text-[13px] text-alert">{error}</p>}

      {panel === "logo" && result && (
        <div className="mt-4">
          {result.monochrome || result.colours.length === 0 ? (
            <p className="text-[13px] text-ink-muted">
              Your logo is black and white, so it has no brand colour to use. Keep one of the themes above, or try a screenshot.
            </p>
          ) : (
            <>
              <p className="text-[13px] text-ink">Which one is your brand colour?</p>
              <div role="group" aria-label="Colours from your logo" className="mt-2 flex flex-wrap gap-2">
                {result.colours.map((colour) => (
                  <button
                    key={colour}
                    type="button"
                    disabled={disabled}
                    onClick={() => onUse({ kind: "logo", colour })}
                    aria-label={`Use ${colour}`}
                    className="rounded-lg border border-line px-2.5 py-2 transition-colors duration-200 hover:border-ember hover:bg-ember-soft"
                  >
                    <Swatch colour={colour} />
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {panel === "screenshot" && result && (
        <div className="mt-4 space-y-2">
          <p className="text-[13px] text-ink">We found these colours{result.is_dark ? " (a dark site)" : ""}:</p>
          <div className="flex flex-wrap gap-4">
            {result.background && <Swatch colour={result.background} label="Background" />}
            {result.primary && <Swatch colour={result.primary} label="Main" />}
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onUse({ kind: "screenshot", colour: result.primary ?? null, background: result.background ?? null, is_dark: result.is_dark ?? false })}
            className="rounded-lg bg-ink px-4 py-2 text-[13px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:opacity-50"
          >
            Use these colours
          </button>
        </div>
      )}

      {panel === "website" && (
        <form
          className="mt-4 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            if (url.trim()) onUse({ kind: "website", url: url.trim() });
          }}
        >
          <label htmlFor="reference-url" className="sr-only">Website address</label>
          <input
            id="reference-url"
            type="text"
            inputMode="url"
            autoComplete="url"
            placeholder="www.example.com"
            value={url}
            disabled={disabled}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-[14px] text-ink placeholder:text-ink-faint focus:border-ember/60 focus:outline-none"
          />
          <button
            type="submit"
            disabled={disabled || !url.trim()}
            className="rounded-lg bg-ink px-4 py-2 text-[13px] font-medium text-paper transition-all duration-200 hover:bg-ember-strong active:translate-y-px disabled:opacity-50"
          >
            Read its style
          </button>
        </form>
      )}
    </div>
  );
}
