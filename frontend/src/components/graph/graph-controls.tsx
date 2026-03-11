"use client";

import { useSigma } from "@react-sigma/core";
import { ZoomIn, ZoomOut, Maximize2, Download } from "lucide-react";
import { useCallback } from "react";

// Overlay controls for the graph canvas
export function GraphControls() {
  const sigma = useSigma();

  const handleZoomIn = useCallback(() => {
    const camera = sigma.getCamera();
    camera.animatedZoom({ duration: 300 });
  }, [sigma]);

  const handleZoomOut = useCallback(() => {
    const camera = sigma.getCamera();
    camera.animatedUnzoom({ duration: 300 });
  }, [sigma]);

  const handleFitToScreen = useCallback(() => {
    const camera = sigma.getCamera();
    camera.animatedReset({ duration: 300 });
  }, [sigma]);

  const handleExportPNG = useCallback(() => {
    const canvas = document.querySelector(".sigma-container canvas") as HTMLCanvasElement | null;
    if (!canvas) return;

    // Create a temporary link to download
    const link = document.createElement("a");
    link.download = "rede-conselheiros.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }, []);

  const buttonClass =
    "flex items-center justify-center w-9 h-9 text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-alt)] transition-colors";

  return (
    <div className="absolute bottom-4 right-4 z-10 flex bg-[var(--color-surface)] shadow-lg border border-[var(--color-border)] overflow-hidden">
      <button
        onClick={handleZoomIn}
        className={buttonClass}
        title="Aproximar"
        type="button"
      >
        <ZoomIn className="h-4 w-4" />
      </button>
      <div className="w-px bg-[var(--color-border)]" />
      <button
        onClick={handleZoomOut}
        className={buttonClass}
        title="Afastar"
        type="button"
      >
        <ZoomOut className="h-4 w-4" />
      </button>
      <div className="w-px bg-[var(--color-border)]" />
      <button
        onClick={handleFitToScreen}
        className={buttonClass}
        title="Ajustar a tela"
        type="button"
      >
        <Maximize2 className="h-4 w-4" />
      </button>
      <div className="w-px bg-[var(--color-border)]" />
      <button
        onClick={handleExportPNG}
        className={buttonClass}
        title="Exportar PNG"
        type="button"
      >
        <Download className="h-4 w-4" />
      </button>
    </div>
  );
}
