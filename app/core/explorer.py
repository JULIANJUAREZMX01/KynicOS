import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from app.utils import get_logger

logger = get_logger(__name__)

class ShadowExplorer:
    """Intelligent indexer and searcher for Julian's projects"""
    
    def __init__(self, base_paths: List[Path]):
        self.base_paths = base_paths
        self.index_file = Path("data/shadow_index.json")
        self.index_data: Dict[str, Any] = {}
        self.is_indexing = False
        
    async def rebuild_index(self):
        """Build a structural and keyword map of all projects"""
        if self.is_indexing:
            return "⚠️ Ya hay una indexación en curso."
            
        self.is_indexing = True
        logger.info("🐕 ShadowExplorer: Iniciando indexación profunda...")
        
        new_index = {
            "projects": {},
            "files": [],
            "timestamp": os.path.getmtime(__file__) if os.path.exists(__file__) else 0
        }
        
        for base_path in self.base_paths:
            if not base_path.exists():
                continue
                
            logger.info(f"Explorando {base_path}...")
            
            for root, dirs, files in os.walk(base_path):
                # Skip heavy or irrelevant dirs
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'dist', 'build', '.astro']]
                
                rel_root = Path(root).relative_to(base_path.parent)
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.rs', '.go', '.md', '.sql', '.env', '.toml')):
                        file_path = Path(root) / file
                        try:
                            stats = file_path.stat()
                            new_index["files"].append({
                                "name": file,
                                "path": str(file_path),
                                "size": stats.st_size,
                                "ext": file_path.suffix
                            })
                        except Exception:
                            continue
                
                # Check for project roots (README, pyproject, etc)
                if 'README.md' in files or 'pyproject.toml' in files or 'package.json' in files:
                    proj_name = Path(root).name
                    new_index["projects"][proj_name] = {
                        "path": str(root),
                        "type": "python/js" if 'pyproject.toml' in files or 'package.json' in files else "generic"
                    }
            
            await asyncio.sleep(0.01) # Cooperate with event loop

        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(new_index, f, indent=2)
            
        self.index_data = new_index
        self.is_indexing = False
        logger.info(f"✅ ShadowExplorer: Indexación completada ({len(new_index['files'])} archivos).")
        return f"✅ Indexación completada. Detecté {len(new_index['projects'])} proyectos y {len(new_index['files'])} archivos de interés."

    def search(self, query: str) -> str:
        """Search the index for relevant files/projects"""
        if not self.index_data and self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index_data = json.load(f)
                
        if not self.index_data:
            return "❌ No hay un índice construido. Usa `rebuild_index` primero."
            
        query = query.lower()
        results = []
        
        # Search projects
        for name, data in self.index_data.get("projects", {}).items():
            if query in name.lower():
                results.append(f"📁 **Proyecto**: {name} -> `{data['path']}`")
                
        # Search files
        count = 0
        for file in self.index_data.get("files", []):
            if query in file["name"].lower() or query in file["path"].lower():
                results.append(f"📄 `{file['path']}`")
                count += 1
                if count > 15: # Limit results
                    results.append("... y más coincidencias.")
                    break
                    
        if not results:
            return "🔍 No encontré coincidencias exactas en el mapa de sombras."
            
        return "🔍 **Hallazgos en el Mapa de Sombras**:\n\n" + "\n".join(results)
