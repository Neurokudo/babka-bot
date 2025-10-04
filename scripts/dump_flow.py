#!/usr/bin/env python3
# scripts/dump_flow.py
"""Скрипт для экспорта схемы меню в Mermaid диаграмму"""

import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ui.menu_schema import MENU, validate_menu_schema
from app.ui.texts import t
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def generate_mermaid_flow():
    """Генерировать Mermaid диаграмму из схемы меню"""
    
    # Валидация схемы
    errors = validate_menu_schema()
    if errors:
        log.error("Schema validation errors:")
        for error in errors:
            log.error(f"  - {error}")
        return None
    
    lines = []
    lines.append("flowchart TD")
    lines.append("")
    
    # Добавляем узлы
    for node_id, node in MENU.items():
        text_key = node.get("text_key", "menu.title")
        title = t(text_key).replace('"', '\\"')  # Экранируем кавычки
        
        # Ограничиваем длину названия для читаемости
        if len(title) > 30:
            title = title[:27] + "..."
        
        lines.append(f'  {node_id}["{title}"]')
    
    lines.append("")
    
    # Добавляем переходы
    for node_id, node in MENU.items():
        for button in node.get("buttons", []):
            target = button.get("to")
            text_key = button.get("text_key", "btn.unknown")
            button_text = t(text_key).replace('"', '\\"')
            
            # Ограничиваем длину текста кнопки
            if len(button_text) > 20:
                button_text = button_text[:17] + "..."
            
            if target and target in MENU:
                lines.append(f'  {node_id} -->|"{button_text}"| {target}')
    
    return "\n".join(lines)

def generate_detailed_flow():
    """Генерировать подробную диаграмму с информацией о callback-ах"""
    
    lines = []
    lines.append("flowchart TD")
    lines.append("")
    
    # Добавляем узлы с дополнительной информацией
    for node_id, node in MENU.items():
        text_key = node.get("text_key", "menu.title")
        title = t(text_key).replace('"', '\\"')
        
        if len(title) > 25:
            title = title[:22] + "..."
        
        # Добавляем информацию о количестве кнопок
        button_count = len(node.get("buttons", []))
        lines.append(f'  {node_id}["{title}<br/>({button_count} кнопок)"]')
    
    lines.append("")
    
    # Добавляем переходы с callback информацией
    for node_id, node in MENU.items():
        for button in node.get("buttons", []):
            target = button.get("to")
            text_key = button.get("text_key", "btn.unknown")
            cb_config = button.get("cb", [])
            
            button_text = t(text_key).replace('"', '\\"')
            if len(button_text) > 15:
                button_text = button_text[:12] + "..."
            
            if target and target in MENU:
                # Добавляем информацию о callback
                if cb_config:
                    action = cb_config[0] if cb_config else "unknown"
                    lines.append(f'  {node_id} -->|"{button_text}<br/>{action}"| {target}')
                else:
                    lines.append(f'  {node_id} -->|"{button_text}"| {target}')
    
    return "\n".join(lines)

def generate_callback_analysis():
    """Генерировать анализ использования callback-ов"""
    
    lines = []
    lines.append("# Анализ callback-ов")
    lines.append("")
    
    # Собираем статистику по действиям
    actions = {}
    for node_id, node in MENU.items():
        for button in node.get("buttons", []):
            cb_config = button.get("cb", [])
            if cb_config:
                action = cb_config[0]
                if action not in actions:
                    actions[action] = []
                actions[action].append({
                    "node": node_id,
                    "button": button.get("text_key", "unknown"),
                    "target": button.get("to")
                })
    
    lines.append("## Статистика действий")
    lines.append("")
    
    for action, usages in sorted(actions.items()):
        lines.append(f"### {action} ({len(usages)} использований)")
        for usage in usages:
            button_text = t(usage["button"])
            lines.append(f"- {usage['node']} → {usage['target']}: {button_text}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    """Основная функция"""
    
    # Создаем папку docs если её нет
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    try:
        # Генерируем основную диаграмму
        log.info("Generating main flow diagram...")
        mermaid_content = generate_mermaid_flow()
        
        if mermaid_content:
            flow_file = docs_dir / "flow.mmd"
            with open(flow_file, "w", encoding="utf-8") as f:
                f.write(mermaid_content)
            log.info(f"Main flow diagram written to {flow_file}")
        else:
            log.error("Failed to generate main flow diagram")
            return 1
        
        # Генерируем подробную диаграмму
        log.info("Generating detailed flow diagram...")
        detailed_content = generate_detailed_flow()
        
        detailed_file = docs_dir / "flow_detailed.mmd"
        with open(detailed_file, "w", encoding="utf-8") as f:
            f.write(detailed_content)
        log.info(f"Detailed flow diagram written to {detailed_file}")
        
        # Генерируем анализ callback-ов
        log.info("Generating callback analysis...")
        analysis_content = generate_callback_analysis()
        
        analysis_file = docs_dir / "callback_analysis.md"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(analysis_content)
        log.info(f"Callback analysis written to {analysis_file}")
        
        # Генерируем сводку по узлам
        log.info("Generating node summary...")
        node_summary = []
        node_summary.append("# Сводка узлов меню")
        node_summary.append("")
        
        for node_id, node in MENU.items():
            text_key = node.get("text_key", "menu.title")
            title = t(text_key)
            buttons = node.get("buttons", [])
            description_key = node.get("description_key")
            
            node_summary.append(f"## {node_id}")
            node_summary.append(f"**Название:** {title}")
            if description_key:
                description = t(description_key)
                node_summary.append(f"**Описание:** {description}")
            node_summary.append(f"**Кнопок:** {len(buttons)}")
            
            if buttons:
                node_summary.append("**Кнопки:**")
                for button in buttons:
                    button_text = t(button.get("text_key", "unknown"))
                    target = button.get("to", "none")
                    cb_config = button.get("cb", [])
                    action = cb_config[0] if cb_config else "none"
                    node_summary.append(f"- {button_text} → {target} ({action})")
            
            node_summary.append("")
        
        summary_file = docs_dir / "node_summary.md"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("\n".join(node_summary))
        log.info(f"Node summary written to {summary_file}")
        
        log.info("All documentation generated successfully!")
        return 0
        
    except Exception as e:
        log.error(f"Error generating documentation: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
