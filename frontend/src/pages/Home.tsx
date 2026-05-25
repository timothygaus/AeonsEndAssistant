import { useNavigate } from "react-router-dom"

function Home() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-12">Aeon's End Assistant</h1>

      <div className="flex flex-col gat-4 w-full max-w-sm">
        <button 
          onClick={() => navigate('/quickplay')}
          className="px-6 py-3 bg-blue-600 rounded text-lg font-semibold hover:bg-blue-700"
        >
          Quickplay
        </button>

        <button 
          onClick={() => navigate('/expedition')}
          className="px-6 py-3 bg-blue-600 rounded text-lg font-semibold hover:bg-blue-700"
        >
          Expedition Mode
        </button>

        <button
          onClick={() => navigate('/sets')}
          className="px-6 py-3 bg-blue-600 rounded text-lg font-semibold hover:bg-blue-700"
        >
          Manage Sets
        </button>
      </div>
    </div>
  )
}

export default Home