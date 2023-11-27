"use strict";

// Global constants and variables
const personalityPicker = document.getElementById("personalityPicker");
const personalityCache = document.getElementById("personalityCache");
const btn = document.getElementById("send");
const username = document.getElementById("username");
const usermail = document.getElementById("useremail");
window.addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    event.preventDefault();
    checkInput();
  }
});
const evtListeners = {
  send: ["click", checkInput],
  username: [
    "change",
    function (event) {
      username.style.color = "#000000";
    },
  ],
  useremail: [
    "change",
    function (event) {
      usermail.style.color = "#000000";
    },
  ],
  personalityPicker: [
    "change",
    function (event) {
      personalityPicker.style.color = "#000000";
      chosePersonality = true;
    },
  ],
};
let chosePersonality = false;

getPersonalities();
setupEventListeners(evtListeners);

/**
 * FUNCTIONS BELOW
 */

function setupEventListeners(evtListener) {
  /** Adds event listeners to ids given in the evtListener dictionary.
   * The event to listen to, and the function to add is given in the value of the dictionary.
   */
  for (const [id, [event, func]] of Object.entries(evtListener)) {
    document.getElementById(id).addEventListener(event, func);
  }
}

function getIP(json) {
  /**
   * get the users ip address
   */
  document.getElementById("ip").value = json.ip;
}

function getPersonalities() {
  /**
   * extract personalities and populates dropdown menu
   */
  /* extract personalities */
  let personalities = personalityCache.value;
  const personalityRegEx = /'([^']*)'/g;
  personalities = personalities.match(personalityRegEx);
  if (personalities) {
    personalities = personalities.map((p) => p.replace(/'/g, ""));
    populateDropDown(personalities);
  }
}

function populateDropDown(personalities) {
  /* populate drop down menu */
  personalities.forEach((p) => {
    const opt = createOptionElement(p);
    personalityPicker.appendChild(opt);
  });
}

function createOptionElement(p) {
  /** create option element */
  const opt = document.createElement("option");
  opt.value = p;
  opt.innerHTML = p;
  return opt;
}

/* validate user input */
function checkInput() {
  var user_form = document.getElementById("userForm");
  // add the .required class to usernameLabel, useremailLabel and personalityPickerLabel if the input is empty
  if (!username.value) {
    document.getElementById("usernameLabel").classList.add("required");
  } else {
    document.getElementById("usernameLabel").classList.remove("required");
  }
  if (!usermail.value) {
    document.getElementById("useremailLabel").classList.add("required");
  } else {
    document.getElementById("useremailLabel").classList.remove("required");
  }
  if (!chosePersonality) {
    document.getElementById("personalityLabel").classList.add("required");
  } else {
    document.getElementById("personalityLabel").classList.remove("required");
  }
  // if the input is not empty, submit the form
  if (username.value && usermail.value && chosePersonality) {
    user_form.submit();
  }
}
