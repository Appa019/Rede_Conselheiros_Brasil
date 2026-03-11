import { Loading } from "@/components/loading";

export default function ExplorerLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loading message="Carregando explorer..." />
    </div>
  );
}
