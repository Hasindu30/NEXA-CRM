export async function checkHealth() {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${baseUrl}/api/v1/health`);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
}
