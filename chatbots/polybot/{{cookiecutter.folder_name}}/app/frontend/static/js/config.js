module.exports = {
  getInTouch:
    "https://pages.erium.de/meetings/theo-steininger/halerium-get-in-touch",
  byeMsg: [
    {
      txt: "Vielen Dank für das Verwenden von Halerium PolyBot! Falls Sie mehr erfahren wollen, ",
    },
    {
      el: "a",
      a_href: this.getInTouch,
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
  ],
};
