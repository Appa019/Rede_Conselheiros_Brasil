import { Loading } from "@/components/loading";

export default function PredictionsLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loading message="Carregando predicoes..." />
    </div>
  );
}
