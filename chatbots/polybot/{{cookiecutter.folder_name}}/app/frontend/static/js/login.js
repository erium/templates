"use strict";

// Global constants and variables
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
};

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
  
  const validEmail = /(?:[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;
  var usermailValid = true;

  if (!usermail.value.match(validEmail)) {
      usermailValid = false;
      document.getElementById("useremailLabel").classList.add("required");
  } else {
    usermailValid = true;
    document.getElementById("useremailLabel").classList.remove("required");
  }

  // if the input is not empty, submit the form
  if (username.value && usermail.value && usermailValid) {
    user_form.submit();
  }
}
