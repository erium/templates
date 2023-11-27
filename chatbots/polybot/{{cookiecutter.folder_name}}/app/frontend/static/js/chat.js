"use strict";

// Global constants and variables
const sessionID = getSessionID("chat_halerium_session_id");
const wsUrl = document.getElementById("wsurl").value;
const ws = new WebSocket(`${wsUrl}prompt?token=${sessionID}`);
const pingPong = setInterval(wsPing, 30000); // prevent websocket from closing
const chat = document.getElementById("chat");
const container = document.getElementById("user-interaction-container");
const userInput = document.getElementById("user-input");
const messages = document.getElementById("messages");
const username = document.getElementById("username");
let openTag = ""; // global storage for open html tags (e.g. <div></div>, openTag = 'div')
const getInTouch =
  "https://pages.erium.de/meetings/theo-steininger/halerium-get-in-touch";
const byeMsg = [
  {
    txt: "Vielen Dank für das Verwenden von Halerium PolyBot! Falls Sie mehr erfahren wollen, ",
  },
  {
    el: "a",
    a_href: getInTouch,
    a_txt: "vereinbaren Sie gerne einen Termin!",
    a_target: "_blank",
  },
  { el: "br" },
  { el: "br" },
  { txt: "Hier geht's zurück zum Login: " },
  {
    el: "a",
    a_href: window.location.origin + "/",
    a_txt: "Login",
    a_target: "_self",
  },
];
const evtListeners = {
  send: ["click", wsSendPrompt],
  "user-input": ["input", resizeTextArea],
  "user-input": [
    "keydown",
    function (event) {
      /**
       * Adds an event listener to the user input text field ("user-iput").
       * On pressing the "Enter" key, will fire the "click()" event of the send button.
       * On pressing "Shift" + "Enter", will add a new line to the prompt text field.
       * On pressing "Backspace" or "Delete", will resize the text field to fit the content.
       */
      if (event.key === "Enter" && event.shiftKey) {
        event.preventDefault();
        userInput.value += "\n";
        resizeTextArea();
        scrollToEndOf(userInput);
      } else if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        document.getElementById("send").click();
      } else if (event.key === "Backspace" || event.key === "Delete") {
        resizeTextArea();
      }
    },
  ],
};

// Page Setup
setupEventListeners(evtListeners);
window.onload = asyncStyling(); // to style the first message
ws.onmessage = wsOnMessage;
// ws.onerror = wsConnectivityProblem;
ws.onclose = wsConnectivityProblem;

/** automatically scroll to the bottom of "chat" when new content is added to it.
 * When a user scroll event is detected, it deactivates.
 * When the user is at the bottom of the chat, it reactivates.
 */
let autoScroll = true;
chat.addEventListener("scroll", function () {
  if (
    chat.scrollTop + chat.clientHeight >=
    chat.scrollHeight - chat.scrollHeight / 100
  ) {
    autoScroll = true;
  } else {
    autoScroll = false;
  }
});
setInterval(function () {
  if (autoScroll) {
    chat.scrollTop = chat.scrollHeight;
  }
}, 50);

function setupEventListeners(evtListener) {
  /** Adds event listeners to ids given in the evtListener dictionary.
   * The event to listen to, and the function to add is given in the value of the dictionary.
   */
  for (const [id, [event, func]] of Object.entries(evtListener)) {
    document.getElementById(id).addEventListener(event, func);
  }
}

// WebSocket Handlers
function wsOnMessage(event) {
  /**
   * waits for messages from the API and adds them to the chat.
   */
  removeLoadingChild();
  parseMessage(event);
}

function wsConnectivityProblem(event) {
  /**
   * Display "book an appointment" message on websocket error
   */
  console.error("WebSocket error observed:", event);
  removeLoadingChild();
  const now = new Date();
  const date = formatDate(now);
  const time = formatTime(now);
  messages.appendChild(createSenderChild("walter", "Halerium", date, time));
  messages.appendChild(createMessageChild("walter"));
  appendToChild(byeMsg);
  //scrollToEndOf(chat);
}

function wsSendPrompt(event) {
  /**
   * Extracts the user query and puts it in the chat, then sends it to the backend.
   */
  // get timestamp
  const now = new Date();
  const date = formatDate(now);
  const time = formatTime(now);
  // get user prompt
  const query = userInput.value;
  const msg = [{ txt: query }];
  // clear prompt text field and resize it accordingly
  userInput.value = "";
  resizeTextArea();
  if (query) {
    // disable send button
    document.getElementById("send").disabled = true;
    // append user prompt to chat
    messages.appendChild(createSenderChild("user", username.value, date, time));
    messages.appendChild(createMessageChild("user"));
    appendToChild(msg);
    asyncStyling(); // currently not working correctly for user messages
    // add waiting animation
    messages.appendChild(createLoadingChild("walter"));
    //scrollToEndOf(chat);
    // send message to API
    ws.send(query);
  }
}

/**
 * Ping-Pong function to prevent websocket from closing
 */
function wsPing() {
  try {
    ws.send("ping, " + sessionID);
  } catch (error) {
    // do nothing (websocket is already closed)
  }
}

/**
 * Helper Functions
 */

function getSessionID(name) {
  /**
   * Searches for the session cookie with name "name" and returns its value.
   * Returns an empty string if no cookie was found.
   */
  const id = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  if (id) {
    return id[2];
  } else {
    return "";
  }
}

function formatDate(date) {
  /**
   * takes a Date() object and returns a formatted, date only, string.
   */
  const day = (date.getDate() < 10 ? "0" : "") + date.getDate();
  const month = (date.getMonth() + 1 < 10 ? "0" : "") + (date.getMonth() + 1);
  const year = date.getFullYear();
  return `${day}.${month}.${year}`;
}

function formatTime(date) {
  /**
   * takes a Date() object and returns a formatted, time only, string.
   */
  const hours = (date.getHours() < 10 ? "0" : "") + date.getHours();
  const minutes = (date.getMinutes() < 10 ? "0" : "") + date.getMinutes();
  const seconds = (date.getSeconds() < 10 ? "0" : "") + date.getSeconds();
  return `${hours}:${minutes}:${seconds}`;
}

function scrollToEndOf(el) {
  /**
   * scrolls to the bottom of the chat window
   */
  el.scrollTop = el.scrollHeight;
}

/**
 * Message helper functions
 */

function createSenderChild(role, name, date, time) {
  /**
   * creates a formatted and filled list item element for Sender and Timestamp of a chat message.
   */
  let child = document.createElement("li");
  child.classList.add(`sender-${role}`);

  const boldText = document.createElement("span");
  boldText.classList.add("name");
  const boldTextNode = document.createTextNode(name);
  boldText.appendChild(boldTextNode);

  const normalText = document.createElement("span");
  normalText.classList.add("timestamp");
  const normalTextNode = document.createTextNode(` ${date}, ${time}`);
  child.appendChild(boldText);
  child.appendChild(normalTextNode);

  return child;
}

function createMessageChild(role) {
  /**
   * creates a list item element for the chat message.
   */
  let child = document.createElement("li");
  child.classList.add(`msg-${role}`);

  return child;
}

function createLoadingChild(role) {
  /**
   * takes a role (to correctly assign the message) and creates a list item child containig a loading animation
   */
  let child = document.createElement("li");
  child.classList.add(`msg-${role}`);
  child.setAttribute("id", "loading-container");
  let loading_dots = document.createElement("div");
  loading_dots.classList.add("loading-dots");
  child.appendChild(loading_dots);

  return child;
}

function removeLoadingChild() {
  /**
   * Removes the loading animation
   */
  const child = document.getElementById("loading-container");
  if (child) {
    child.remove();
  }
}

function appendToChild(msg_array) {
  const items = document.getElementsByTagName("li");
  const child = items[items.length - 1];

  msg_array.forEach((msg_dict) => {
    for (let key in msg_dict) {
      if (openTag) {
        let writeToTag = document.getElementsByTagName(openTag);
        writeToTag = writeToTag[writeToTag.length - 1];
        switch (key) {
          case "el":
            if (msg_dict[key] === openTag) {
              openTag = "";
              break;
            }
          case "txt":
            let txt = document.createTextNode(msg_dict[key]);
            writeToTag.appendChild(txt);
            break;
        }
      } else {
        switch (key) {
          case "el":
            let el = document.createElement(msg_dict[key]);
            switch (msg_dict[key]) {
              case "a":
                el.href = msg_dict["a_href"];
                el.textContent = msg_dict["a_txt"];
                el.target = msg_dict["a_target"];
                break;
              case "pre":
                openTag = "pre";
                break;
            }
            child.appendChild(el);
            break;
          case "txt":
            let txt = document.createTextNode(msg_dict[key]);
            child.appendChild(txt);
            break;
        }
      }
    }
  });
}

function asyncStyling() {
  /**
   * Looks at the generated text and restyles it if necessary.
   * used for bold (*abc*), italic (**abc**), and strike-through
   */
  // get latest list item
  const items = document.getElementsByTagName("li");
  const child = items[items.length - 1];
  let txt = child.innerHTML;
  // text styling regex
  const regex_bold = /\*{2}([^\*]+)\*{2}/g; // **abc**
  const regex_bold_alt = /\_{2}([^\_]+)\_{2}/g; // __abc__
  const regex_italic = /\*{1}([^\*]+)\*{1}/g; // *abc*
  const regex_italic_alt = /\_{1}([^\_]+)\_{1}/g; // _abc_
  const regex_link = /\[([^\]]+)\]\(([^\)]+)\)/g; // [abc](def)
  const regex_single_backtick = /\`([^\` \n]+)\`/g; // `abc`
  const regex_backtick_newline = /\`\n\n/g; // `\n\n (left over from end of code block)

  // handle bold
  let match_bold;
  while (
    (match_bold = regex_bold.exec(txt)) !== null ||
    (match_bold = regex_bold_alt.exec(txt)) !== null
  ) {
    let boldElement = document.createElement("span");
    boldElement.appendChild(document.createTextNode(match_bold[1]));
    boldElement.style.fontFamily = "IntroCond-SemiBoldAlt";
    // replace in DOM
    txt = txt.replace(match_bold[0], boldElement.outerHTML);
  }

  // handle italic
  let match_italic;
  while (
    (match_italic = regex_italic.exec(txt)) !== null ||
    (match_italic = regex_italic_alt.exec(txt)) !== null
  ) {
    let italicElement = document.createElement("span");
    italicElement.appendChild(document.createTextNode(match_italic[1]));
    italicElement.style.fontStyle = "italic";
    // replace in DOM
    txt = txt.replace(match_italic[0], italicElement.outerHTML);
  }

  // handle links
  let match_link;
  while ((match_link = regex_link.exec(txt)) !== null) {
    let linkElement = document.createElement("a");
    linkElement.appendChild(document.createTextNode(match_link[1]));
    linkElement.href = match_link[2];
    linkElement.target = "_blank";
    // replace in DOM
    txt = txt.replace(match_link[0], linkElement.outerHTML);
  }

  // handle single backticks
  let match_single_backtick;
  while ((match_single_backtick = regex_single_backtick.exec(txt)) !== null) {
    let codeElement = document.createElement("span");
    codeElement.appendChild(document.createTextNode(match_single_backtick[1]));
    codeElement.style.fontFamily = "monospace";
    // replace in DOM
    txt = txt.replace(match_single_backtick[0], codeElement.outerHTML);
  }

  // handle backticks with newline to detect end of code blocks
  // two tokens are used: `` and `\n\n
  // first one is handled live by parseMessage, second one is handled here
  let match_backtick_newline;
  while ((match_backtick_newline = regex_backtick_newline.exec(txt)) !== null) {
    let hideElement = document.createElement("br");
    // replace in DOM
    txt = txt.replace(match_backtick_newline[0], hideElement.outerHTML);
  }

  child.innerHTML = txt; // update the child element with the new styled text
}

function parseMessage(event) {
  /**
   * Parse the received message and add it to the chat using message helper functions.
   */
  const now = new Date();
  const date = formatDate(now);
  const time = formatTime(now);
  let msg = [];

  // get message from API
  let content = document.createTextNode(event.data);

  // add response to chat window
  switch (content.textContent) {
    case "<sos>":
      messages.appendChild(createSenderChild("walter", "Halerium", date, time));
      messages.appendChild(createMessageChild("walter"));
      break;
    case "<src>":
      msg = [{ el: "br" }, { txt: "Sources: " }, { el: "br" }];
      appendToChild(msg);
      break;
    case "<link>":
      msg = [
        {
          el: "a",
          a_href: getInTouch,
          a_txt: "vereinbaren Sie gerne einen Termin!",
        },
      ];
      appendToChild(msg);
      //scrollToEndOf(chat);
      break;
    case content.textContent.match(/(\`\`+)/)?.input:
      // finds code blocks ("``" and more)
      // single ` is already styled by asyncStyling(), because that is fast enough.
      msg = [
        {
          el: "pre",
        },
      ];
      appendToChild(msg);
      //scrollToEndOf(chat);
      break;
    // case content.textContent.match(/\`/)?.input: // edge case: "`\n\n" is a token sent after the end of code. \n is already caught by css.
    //   // do nothing
    //   //scrollToEndOf(chat);
    //   break;
    case "<eos>":
      // enable button again
      document.getElementById("send").disabled = false;
      break;
    case "<deactivate>":
      document.getElementById("send").disabled = true;
      document.getElementById("prompt").disabled = true;
      break;
    case "<pong>":
      // do nothing, just a ping-pong message
      break;
    default:
      msg = [{ txt: content.textContent }];
      appendToChild(msg);
      //scrollToEndOf(chat);
      break;
  }
  // style already existing message
  asyncStyling();
}

function resizeTextArea() {
  /**
   * This function resizes the text area to fit the content.
   */
  userInput.style.height = "auto";
  container.style.height = "auto";
  chat.style.marginBottom = "100px";
  userInput.style.height = userInput.scrollHeight + "px";
  container.style.height = userInput.scrollHeight + "px";
  chat.style.marginBottom += userInput.scrollHeight + "px";
}
