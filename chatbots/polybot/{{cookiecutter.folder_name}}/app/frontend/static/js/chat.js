"use strict";

class ChatManager {
  /**
   * Constructor for ChatManager.
   * Initializes all necessary elements, sets up event listeners,
   * starts auto-scroll for chat, and initializes WebSocket connection.
   */
  constructor() {
    this.initializeSessionAndUrls();
    this.initializeChatElements();
    this.initializeInteractionElements();
    this.initializeGetInTouchAndByeMessage()
    this.setupEventListeners();
    this.autoScrollChat();
    this.initializeWebSocket();
    this.pingPong = this.wsPingPong(); // websocket keep-alive
    this.renderer = new marked.Renderer();
    this.renderer.paragraph = (text) => {
      return `${text}`; // Customize as needed
    };
    this.renderer.listitem = (text) => {
        return `<li style="padding:0; margin:0;">${text}</li>`;
    };
    this.renderer.code = (code, language) => {
        var btn_ctc = '<button class="copy-btn" onclick="window.chatManager.copyToClipboard(this)">Copy code</button>';
        var lang_lbl = `<span class="lang-lbl">${language}</span>`;
        var escapedCode = this.escapeHTML(code);
        return `<pre>${lang_lbl}${btn_ctc}<code class=hljs ${language}>${escapedCode}</code></pre>`
    }

    marked.setOptions({ renderer: this.renderer });
  }

  /**
   * Initializes session details and URLs for WebSocket and application.
   */
  initializeSessionAndUrls() {
    this.sessionId = this.getSessionId("chat_halerium_session_id");
    this.wsUrl = document.getElementById("wsurl").value;
    this.appUrl = document.getElementById("appurl").value;
  }

  /**
   * Initializes chat elements including bot name, user name, and message containers.
   */
  initializeChatElements() {
    this.botName = document.getElementById("botname").value;
    this.userName = document.getElementById("username").value;
    this.chat = document.getElementById("chat");
    this.messages = document.getElementById("messages");
  }

  /**
   * Initializes elements related to user interaction.
   */
  initializeInteractionElements() {
    this.userInteractionContainer = document.getElementById("user-interaction-container");
    this.userInput = document.getElementById("user-input");
  }

  /**
   * Initializes the contact link and the goodbye message for the chat.
   */
  initializeGetInTouchAndByeMessage() {
    this.getInTouch = "https://pages.erium.de/meetings/theo-steininger/halerium-get-in-touch";
    this.byeMessage = `Vielen Dank für das Verwenden von ${this.botName}. 
                      Falls Sie mehr erfahren wollen, [vereinbaren Sie gerne einen Termin](${this.getInTouch}).
                      Hier geht's zurück zum Login: [Login](${this.appUrl})`;
  }

  /**
   * Sets up the WebSocket connection and its event handlers.
   */
  initializeWebSocket() {
    this.ws = new WebSocket(`${this.wsUrl}prompt?token=${this.sessionId}`);
    this.ws.onmessage = (event) => this.handleWsMessage(event);
    this.ws.onclose = (event) => this.handleWsConnectivityProblem(event);
    this.ws.onerror = (error) => {
      console.error("WebSocket encountered an error:", error);
    };
  }

  /**
   * Sets up various event listeners for chat and user input.
   */
  setupEventListeners() {
    this.setupChatScrollListener();
    this.setupInputListeners();
  }

  /**
   * Adds a scroll event listener to the chat element to handle auto-scrolling.
   */
  setupChatScrollListener() {
    this.chat.addEventListener("scroll", () => {
      this.autoScroll = this.chat.scrollTop + this.chat.clientHeight >=
                        this.chat.scrollHeight - this.chat.scrollHeight / 100;
    });
  }

  /**
   * Sets up event listeners for user input, including send button and keyboard interactions.
   */
  setupInputListeners() {
    // Send Button Click Listener
    document.getElementById("send").addEventListener("click", () => this.sendMessage());

    // User Input Listeners
    this.userInput.addEventListener("input", () => this.resetUserInputAreaSize());
    this.userInput.addEventListener("keydown", (event) => this.handleUserInputKeydown(event));
  }

  /**
   * Sends a periodic 'ping' message over WebSocket to keep the connection alive.
   */
  wsPingPong() {
    setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(`ping, ${this.sessionId}`);
        } catch (error) {
          console.error(`Ping failed: ${error}`);
        }
      }
    }, 30000);
  }

  copyToClipboard(btn) {
      var text = btn.nextElementSibling.textContent;
      navigator.clipboard.writeText(text).then(function() {
        btn.textContent = "\u2713 Copied!"; // ✓
        setTimeout(() => {
            btn.textContent = "Copy code";
        }, 2000);
      }).catch(function(err) {
        console.error('Error in copying text: ', err);
      });
  }

  escapeHTML(str) {
    return str.replace(/[&<>'"]/g, function(tag) {
        const charsToReplace = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '\'': '&#39;',
            '"': '&quot;'
        };
        return charsToReplace[tag] || tag;
    });
  }

  /**
   * Handles keyboard input in the user input area, especially for sending messages.
   */
  handleUserInputKeydown(event) {
      if (event.key === "Enter") {
          event.preventDefault();
          if (event.shiftKey) {
              this.userInput.value += "\n";
              this.resetUserInputAreaSize();
          } else {
              this.sendMessage();
          }
      }
  }

  /**
   * Handles incoming WebSocket messages.
   */
  handleWsMessage(event) {
    this.removeThinkingIndicator();
    this.displayAssistantMessage(event.data);
  }

  /**
   * Handles connectivity issues with the WebSocket.
   */
  handleWsConnectivityProblem(event) {
    console.error("WebSocket error observed:", event);
    this.removeThinkingIndicator();
    this.appendStandaloneMessageToChat("assistant", this.byeMessage);
    this.scrollToBottomOfElement(chat);
  }

  /**
   * Sends the user's message to the chat and performs necessary UI updates.
   */
  sendMessage() {
    const query = this.getUserInput();
    if (query) {
      this.sendButtonDisabled(true);
      this.displayUserMessage(query);
      this.sendMessageToServer(query);
      this.clearUserInput();
      this.showThinkingIndicator();
      this.scrollToBottomOfElement();
      }
  }

  /**
   * Sends the user's message to the server via WebSocket.
   * @param {string} query - The message text to be sent.
   */
  sendMessageToServer(query) {
    try {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(query);   
      } else {
        console.error("WebSocket not open. Message not sent.");
        this.appendStandaloneMessageToChat("assistant", "I'm sorry, but your message could not be sent.");
      }
    } catch (error) {
      console.error(`Error sending message: ${error}`);
      this.appendStandaloneMessageToChat("assistant", "I'm sorry, but your message could not be sent.");
    }
  }

  /**
   * Enables or disables the send button.
   * @param {boolean} state - True to disable the button, false to enable it.
   */
  sendButtonDisabled(state) {
    document.getElementById("send").disabled = state;
  }

  /**
   * Appends the user's message to the chat interface.
   * @param {string} query - The message text from the user.
   */
  displayUserMessage(query) {
    this.appendStandaloneMessageToChat("user", query);
  }

  /**
   * Appends the assistant's message to the chat interface.
   * @param {string} response - The message text from the assistant.
   */
  displayAssistantMessage(response) {
    this.appendStreamedMessageToChat("assistant", response);
  }

  /**
   * Automatically scrolls the chat content.
   * Continuously checks and adjusts the scroll position to reveal new messages.
   */
  autoScrollChat() {
    setInterval(() => {
        if (this.autoScroll) {
            this.chat.scrollTop = this.chat.scrollHeight;
        }
    }, 50);
  }

  /**
   * Returns the current value of the user input text area.
   */
  getUserInput() {
    return this.userInput.value.trim();
  }

  /**
   * Returns the current session ID from cookies.
   */
  getSessionId(key) {
    const id = document.cookie.match(new RegExp("(^| )" + key + "=([^;]+)"));
    if (id) {
      return id[2];
    } else {
      return "";
    }
  }

  /**
   * Returns the current timestamp as a string.
   * Format: dd.mm.yyyy, HH:MM:SS
   */
  static getCurrentTimestamp() {
    const date = new Date();
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${day}.${month}.${year}, ${hours}:${minutes}:${seconds}`;
  }

  /**
   * Clears the user input field and resets its size.
   */
  clearUserInput() {
    // clear prompt text field and resize it accordingly
    this.userInput.value = "";
    this.resetUserInputAreaSize();
  }

  /**
   * Dynamically adjusts the size of the user input area based on its content.
   * Ensures the chat interface accommodates the varying size of the input area.
   */
  resetUserInputAreaSize() {
    this.userInput.style.height = "auto";
    this.userInteractionContainer.style.height = "auto";
    this.chat.style.marginBottom = "100px";
    this.userInput.style.height = this.userInput.scrollHeight + "px";
    this.userInteractionContainer.style.height = this.userInput.scrollHeight + "px";
    this.chat.style.marginBottom += this.userInput.scrollHeight + "px";
  }

  /**
   * Applies filters to the incoming text chunks/tokens
   */
  filterFunctionCallContent(content) {
    // Remove all function call related messages
    const blockQuoteFilterPattern = new RegExp("\\n?>.*\\n*", "gm");
    const resultNumberFilterPattern = new RegExp("^Result \\d+\\n*", "gm");
    const blockCommentEndFilterPattern = new RegExp("-->\\n*", "gm");
    const functionCallEndFilterPattern = new RegExp("[\\r\\n]*--------------------------------------[\\r\\n]*", "g");
    
    content = content.replace(blockCommentEndFilterPattern, ''); // has to be first!
    content = content.replace(blockQuoteFilterPattern, '');
    content = content.replace(resultNumberFilterPattern, '');
    content = content.replace(functionCallEndFilterPattern, '');
  
    return content;
  }

  /**
   * Appends a standalone message to the chat interface.
   * Used for messages that are not part of a streamed conversation.
   * @param {string} role - The role of the message sender (e.g., 'user', 'assistant').
   * @param {string} messageText - The text of the message to be appended.
   */
  appendStandaloneMessageToChat(role, messageText) {
    // get current timestamp
    const timestamp = ChatManager.getCurrentTimestamp();

    // create list item for sender and timestamp line
    const senderListItem = document.createElement("li");
    senderListItem.className = `sender-${role}`;

    const senderNameSpan = document.createElement("span");
    senderNameSpan.className = "name";
    senderNameSpan.textContent = role === "user" ? this.userName + " " : this.botName + " ";

    const timestampSpan = document.createElement("span");
    timestampSpan.className = "timestamp";
    timestampSpan.textContent = timestamp;

    senderListItem.appendChild(senderNameSpan);
    senderListItem.appendChild(timestampSpan);

    // create list item for message text
    const messageListItem = document.createElement("li");
    messageListItem.className = `msg-${role}`;

    const messageTextSpan = document.createElement("span");
    messageTextSpan.textContent = messageText;
    messageListItem.appendChild(messageTextSpan);

    const messagesContainer = document.getElementById("messages");
    messagesContainer.appendChild(senderListItem);
    messagesContainer.appendChild(messageListItem);

    this.parseMarkdown(messageTextSpan)
  }

  /**
   * Handles the appending of streamed messages to the chat interface.
   * This method manages the state of messages being received in parts.
   * @param {string} role - The role of the message sender (e.g., 'user', 'assistant').
   * @param {string} messageText - The text of the message or control tokens like <sos>, <eos>.
   */
  appendStreamedMessageToChat(role, messageText) {
    
    const currentTextSpan = document.getElementById("currSpan");

    switch (messageText) {

      case "<sos>":
        // get current timestamp
        const timestamp = ChatManager.getCurrentTimestamp();

        // create list item for sender and timestamp line
        const senderListItem = document.createElement("li");
        senderListItem.className = `sender-${role}`;

        const senderNameSpan = document.createElement("span");
        senderNameSpan.className = "name";
        senderNameSpan.textContent = role === "user" ? this.userName + " " : this.botName + " ";

        const timestampSpan = document.createElement("span");
        timestampSpan.className = "timestamp";
        timestampSpan.textContent = timestamp;

        senderListItem.appendChild(senderNameSpan);
        senderListItem.appendChild(timestampSpan);

        // create list item for message text
        const messageListItem = document.createElement("li");
        messageListItem.className = `msg-${role}`;

        const messageTextSpan = document.createElement("span");
        messageTextSpan.id = "currSpan"
        messageListItem.appendChild(messageTextSpan);

        const messagesContainer = document.getElementById("messages");
        messagesContainer.appendChild(senderListItem);
        messagesContainer.appendChild(messageListItem);
        break;
      
      case "<eos>":
        this.parseMarkdown(currentTextSpan);
        document.querySelectorAll('pre code:not(.highlighted)').forEach((block) => {
            hljs.highlightElement(block);
            block.classList.add('highlighted');
        });
        currentTextSpan.id = "";
        this.sendButtonDisabled(false);
        break;
      
      case "<pong>":
        break;

      default:
        messageText = this.filterFunctionCallContent(messageText);
        if (messageText) {
          currentTextSpan.textContent += messageText;
        }
        break;
    }
  }

  /**
   * Parses markdown text from an element and converts it into HTML.
   * Then sets the parsed content as innerHTML of that element.
   * @param {HTMLElement} el - The element containing the markdown text.
   */
  parseMarkdown(el) {
    const value = el.textContent.trim();
    const parsedValue = marked.parse(value);
    el.innerHTML = parsedValue;
  }

  /**
   * Displays a visual indicator that the assistant is processing/thinking.
   * @param {string} [role='assistant'] - The role of the message sender.
   */
  showThinkingIndicator(role = "assistant") {
    const loadingListItem = document.createElement("li");
    loadingListItem.className = `msg-${role}`;
    loadingListItem.id = "loading-container";

    const loadingDots = document.createElement("div");
    loadingDots.className = "loading-dots";

    loadingListItem.appendChild(loadingDots);

    const messagesContainer = document.getElementById("messages");
    messagesContainer.appendChild(loadingListItem);
  }

  /**
   * Removes the thinking indicator from the chat interface.
   */
  removeThinkingIndicator() {
    const loadingContainer = document.getElementById("loading-container");
    if (loadingContainer) {
      loadingContainer.remove();
      }
  }

  /**
   * Scrolls the specified element to its bottom.
   * Typically used to keep the chat scrolled to the latest message.
   * @param {HTMLElement} [el=this.chat] - The element to scroll.
   */
  scrollToBottomOfElement(el = this.chat) {
    el.scrollTop = el.scrollHeight;
  }
}

window.onload = () => {
  document.getElementById("fmt").innerHTML = ChatManager.getCurrentTimestamp();
  window.chatManager = new ChatManager();
};