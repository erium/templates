/*
// add event listener for file upload
upload_button = document.getElementById('upload');
file_input = document.getElementById('file');
upload_button.addEventListener('click', function (event) {
  file_input.click()
});
file_input.addEventListener('change', uploadFile);
function uploadFile() {
  messages = document.getElementById("messages");
  now = new Date();

  // disable further user input
  document.getElementById('send').disabled = true;
  document.getElementById('upload').disabled = true;
  document.getElementById('prompt').disabled = true;

  // inform user about what's going on
  item = document.createElement("li");
  item.classList.add("sender-walter");
  item.appendChild(document.createTextNode("Walter (" + now.today() + " @ " + now.timeNow() + ")"));
  messages.appendChild(item);
  item = document.createElement("li");
  item.classList.add("msg-walter");
  messages.appendChild(item);
  item.appendChild(document.createTextNode('Uploading your document and learning about it. Please wait until the page reloads.'))
  // add waiting animation
  child = document.createElement('li');
  child.classList.add('msg-walter');
  child.setAttribute('id', 'loading-container');
  loading_dots = document.createElement('div');
  loading_dots.classList.add('loading-dots');
  child.appendChild(loading_dots);
  messages.appendChild(child);

  // submit document
  document.getElementById('upload_form').submit();
} */
