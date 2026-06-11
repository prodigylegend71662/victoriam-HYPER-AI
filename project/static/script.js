document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('queryInput');
  const btn = document.getElementById('submitBtn');
  const messages = document.getElementById('messages');

  function appendBubble(text, role = 'user') {
    const li = document.createElement('li');
    li.className = `message ${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    renderMessageContent(text, bubble);
    li.appendChild(bubble);
    messages.appendChild(li);
    messages.scrollTop = messages.scrollHeight;
    return li;
  }

  function appendParagraphs(result) {
    const parts = result.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
    parts.forEach(p => appendBubble(p, 'assistant'));
  }

  function renderMessageContent(text, container) {
    const blocks = text.replace(/\r/g, '').split(/\n\s*\n/).map(b => b.trim()).filter(Boolean);
    blocks.forEach(block => {
      const lines = block.split(/\n/);
      let paragraph = null;

      lines.forEach(line => {
        const headerMatch = line.match(/^(={2,6})\s*(.+?)\s*\1(?:\s+(.*))?$/);
        if (headerMatch) {
          if (paragraph) {
            paragraph = null;
          }
          const level = Math.min(headerMatch[1].length, 6);
          const header = document.createElement(`h${level}`);
          header.innerText = headerMatch[2];
          container.appendChild(header);
          if (headerMatch[3]) {
            paragraph = document.createElement('p');
            paragraph.innerText = headerMatch[3];
            container.appendChild(paragraph);
          }
        } else {
          if (!paragraph) {
            paragraph = document.createElement('p');
            container.appendChild(paragraph);
          } else {
            paragraph.appendChild(document.createElement('br'));
          }
          paragraph.appendChild(document.createTextNode(line));
        }
      });
    });
  }

  btn.addEventListener('click', send);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    appendBubble(text, 'user');

    // assistant placeholder
    const placeholder = appendBubble('Thinking...', 'assistant');
    btn.disabled = true;
    input.disabled = true;

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      const result = data.result || '';
      placeholder.remove();
      appendParagraphs(result);
    } catch (e) {
      placeholder.querySelector('.bubble').innerText = 'Error: could not reach the server.';
    } finally {
      btn.disabled = false;
      input.disabled = false;
      messages.scrollTop = messages.scrollHeight;
    }
  }
});
