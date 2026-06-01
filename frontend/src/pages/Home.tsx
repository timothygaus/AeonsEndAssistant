import { useNavigate } from "react-router-dom"
import Button from "../components/Button"

function Home() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-12">Aeon's End Assistant</h1>
      <div className="flex flex-col gap-4 w-full max-w-sm">
        <Button onClick={() => navigate('/quickplay')}>Quickplay</Button>
        <Button onClick={() => navigate('/expedition')}>Expedition Mode</Button>
        <Button onClick={() => navigate('/sets')}>Manage Sets</Button>
      </div>
    </div>
  )
}

export default Home
