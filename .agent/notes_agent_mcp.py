import sqlite3
import os
import json
import sys
from mcp.server.fastmcp import FastMCP

# Define the DB path relative to the root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'notes.db')

# Initialize FastMCP server
mcp = FastMCP("NotesManager")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def get_user_summary(username: str) -> str:
    """Provides a high-level summary of a user's notes count and recent activity."""
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user:
        conn.close()
        return f"User '{username}' not found."
    
    notes_count = conn.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user['id'],)).fetchone()[0]
    recent_note = conn.execute('SELECT title, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user['id'],)).fetchone()
    
    conn.close()
    
    summary = f"User '{username}' has {notes_count} notes."
    if recent_note:
        summary += f" Most recent note: '{recent_note['title']}' created on {recent_note['created_at']}."
    
    return summary

@mcp.tool()
def search_private_notes(username: str, query: str) -> str:
    """Searches for notes belonging to a specific user containing the query string."""
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user:
        conn.close()
        return f"User '{username}' not found."
    
    notes = conn.execute(
        "SELECT title, content FROM notes WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)",
        (user['id'], f'%{query}%', f'%{query}%')
    ).fetchall()
    
    conn.close()
    
    if not notes:
        return f"No notes found for user '{username}' matching '{query}'."
    
    results = [f"Title: {n['title']}\nContent: {n['content']}" for n in notes]
    return "---\n".join(results)

@mcp.tool()
def security_audit_notes(username: str) -> str:
    """Scans user's notes for potentially sensitive plain-text information like passwords or API keys."""
    # Simple pattern matching for demonstration
    sensitive_patterns = ['password', 'secret', 'key', 'token', 'apikey', 'pwd']
    
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user:
        conn.close()
        return f"User '{username}' not found."
    
    notes = conn.execute('SELECT id, title, content FROM notes WHERE user_id = ?', (user['id'],)).fetchall()
    conn.close()
    
    findings = []
    for note in notes:
        content_lower = note['content'].lower()
        title_lower = note['title'].lower()
        
        for pattern in sensitive_patterns:
            if pattern in content_lower or pattern in title_lower:
                findings.append(f"Potential sensitive info found in note ID {note['id']} ('{note['title']}') matching pattern '{pattern}'")
                break
                
    if not findings:
        return f"No sensitive information patterns detected in notes for user '{username}'."
    
    return "\n".join(findings)

if __name__ == "__main__":
    mcp.run()
