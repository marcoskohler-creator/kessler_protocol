#!/bin/bash

echo "=========================================="
echo "🛡️ Deploying The Kessler Protocol..."
echo "=========================================="
echo ""

mkdir -p ~/.gemini/config/skills/kessler-protocol
mkdir -p ~/.gemini/config/hooks

# Copiando a Constituição Kessler para o formato lido pelo motor Antigravity
# Nota: Se estiver usando o Cursor, mude o destino para ~/.cursorrules
# Se estiver usando Claude Code, adapte para CLAUDE.md
cp KESSLER_CONSTITUTION.md ~/.gemini/GEMINI.md

cp config/skills/kessler-protocol/SKILL.md ~/.gemini/config/skills/kessler-protocol/SKILL.md
cp config/hooks/pre-flight-check.sh ~/.gemini/config/hooks/pre-flight-check.sh
cp config/hooks/post-flight-verify.sh ~/.gemini/config/hooks/post-flight-verify.sh
chmod +x ~/.gemini/config/hooks/*.sh

echo "Core architectural rules injected."
echo "------------------------------------------"
echo "🧠 SELECT YOUR AI PERSONA"
echo "------------------------------------------"
echo "The Kessler Protocol allows you to define how your AI communicates."
echo "1) Apex Nerd (Sci-Fi, Cyberpunk, Hacker vibe - Relaxed but lethal)"
echo "2) Corporate Architect (Strict, formal, enterprise-level)"
echo "3) Silent Executioner (Code only, zero small talk)"
echo "4) Skip (Keep default)"
read -p "Select an option [1-4]: " persona_choice

echo "" >> ~/.gemini/GEMINI.md
echo "## 6. COMUNICAÇÃO E PERSONA" >> ~/.gemini/GEMINI.md

case $persona_choice in
  1)
    echo "- **Apex Nerd:** Aja como um parceiro de co-op. Tom de trincheira de código. Use referências de Sci-Fi, Cyberpunk, Matrix e Cultura Nerd para explicar arquitetura." >> ~/.gemini/GEMINI.md
    echo "✅ Persona: Apex Nerd activated."
    ;;
  2)
    echo "- **Corporate Architect:** Comunicação estritamente profissional, corporativa e formal. Foco em jargões de C-Level e engenharia Enterprise." >> ~/.gemini/GEMINI.md
    echo "✅ Persona: Corporate Architect activated."
    ;;
  3)
    echo "- **Silent Executioner:** Zero conversa. Responda apenas com o código modificado e o status da operação." >> ~/.gemini/GEMINI.md
    echo "✅ Persona: Silent Executioner activated."
    ;;
  *)
    echo "- **Padrão:** Comunicação técnica padrão." >> ~/.gemini/GEMINI.md
    echo "✅ Persona: Default activated."
    ;;
esac

echo "=========================================="
echo "✅ Installation Complete! The chain reaction is contained."
echo "=========================================="
