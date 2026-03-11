import { Loading } from "@/components/loading";

export default function MembersLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loading message="Carregando membros..." />
    </div>
  );
}
