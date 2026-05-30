import { useNavigate } from "react-router-dom";

function BackButton() {
    const navigate = useNavigate()

    return (
        <button
            onClick={() => navigate(-1)}
            className="text-gray-400 hover:text-white text-sm mb-4 items-center gap-1"
        >
            Back
        </button>
    )
}

export default BackButton