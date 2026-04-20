# Claude BambuLab Printer Integration

An advanced AI-powered 3D printing ecosystem that integrates **Claude** with **BambuLab printers**, **OpenSCAD**, **Blender**, and **MakerWorld**. This project allows you to generate, search, and manage 3D prints using natural language.

## 🚀 Key Features

### 1. Dual-Engine 3D Generation
*   **OpenSCAD (Default):** Best for mechanical, parametric, and functional parts. Generates clean, structured code with material-specific tolerances.
*   **Blender (Organic):** Automatically switches to Blender for organic shapes and high-fidelity "hero" renders.
*   **Material-Aware Design:** Automatically adjusts wall thickness, clearances, and print settings based on the selected material (PLA, PETG, TPU, ABS, ASA, etc.).

### 2. MakerWorld Integration
*   **Natural Language Search:** Find existing models on MakerWorld without leaving the chat.
*   **Automated Download:** Search, select, and download models directly to your workspace.

### 3. Printer Control & Monitoring
*   **BambuLab Integration:** Send 3MF files directly to your printer.
*   **Real-time Monitoring:** Check print status, progress, and camera feeds.
*   **Control:** Pause, resume, or cancel prints via natural language commands.

### 4. Advanced Validation & Repair
*   **Mesh Auditing:** Uses Blender to inspect meshes for non-manifold geometry and common FDM printing risks.
*   **Auto-Repair:** Attempts to fix common mesh issues before printing.

---

## 🛠 Project Structure

The project is divided into three main components:

### 📁 `.claude/skills/print/`
The core logic for the Claude skill, including:
*   **`SKILL.md`**: The system prompt and routing logic for Claude.
*   **`scripts/`**: Python scripts for Blender automation, MakerWorld searching, and printer control.
*   **`reference/`**: Documentation for OpenSCAD best practices, materials, and print settings.

### 📁 `backend/`
A FastAPI-based backend that orchestrates the communication between Claude, the local file system, and the BambuLab APIs.
*   **Tech Stack:** FastAPI, Pydantic, Claude Agent SDK, Poetry.

### 📁 `frontend/`
A modern React dashboard for monitoring prints and managing your 3D model library.
*   **Tech Stack:** React 19, Vite, TypeScript, TailwindCSS.

---

## ⚙️ Installation

### Prerequisites
*   **Python 3.11+**
*   **Node.js & npm**
*   **OpenSCAD** (for parametric generation)
*   **Blender** (for organic generation and rendering)
*   **Poetry** (for backend dependency management)

### Backend Setup
```bash
cd backend
poetry install
cp .env.example .env  # Add your API keys and printer credentials
poetry run uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Claude Skill Setup
To use this as a Claude skill, ensure the `.claude/skills/print/` directory is accessible to your Claude Desktop or CLI configuration.

---

## 📖 Usage Examples

*   **Generate:** "Create a parametric box for a Raspberry Pi 5 with a snap-fit lid."
*   **Search:** "Find a cool geometric planter on MakerWorld."
*   **Print:** "Send the latest generated model to my Bambu A1 using PLA."
*   **Status:** "How is the print doing? Send me a screenshot of the camera."
*   **Audit:** "Is `model.stl` printable? Check for non-manifold edges."

---

## 🤝 Contributing
Contributions are welcome! Please check the `docs/` directory for detailed design specifications and integration plans.

## 📄 License
MIT License - See [LICENSE](LICENSE) for details.
