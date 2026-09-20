import { checkHealth } from "@/lib/api";

export default async function Home() {
  let healthStatus = "Unknown";
  try {
    const data = await checkHealth();
    healthStatus = data.status;
  } catch {
    healthStatus = "Error fetching health";
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">CRM SaaS Frontend</h1>
      <p className="text-xl">
        Backend status: <span className="font-semibold text-blue-500">{healthStatus}</span>
      </p>
    </main>
  );
}
