// In-page confirmation modal.
//
// We deliberately do NOT use the native confirm() to gate actions. Chrome
// offers "Prevent this page from creating additional dialogs" after a couple
// of native dialogs; once checked, every confirm() returns false instantly
// and silently until the page is reloaded — which made the Print/Reprint and
// Void buttons appear dead. This modal can't be suppressed that way.
//
// Any element with a data-confirm="message" attribute is intercepted: the
// modal is shown, and the element's real action only runs if the user
// confirms. Supported elements:
//   - <a data-confirm ...>            -> opens href (honoring target) on OK
//   - <button type=submit data-confirm> -> submits its form on OK
(function () {
  var overlay = document.getElementById("modal-overlay");
  var message = document.getElementById("modal-message");
  var okBtn = document.getElementById("modal-ok");
  var cancelBtn = document.getElementById("modal-cancel");
  if (!overlay) return;

  var pending = null;

  function show(text, onOk) {
    message.textContent = text;
    pending = onOk;
    overlay.hidden = false;
    okBtn.focus();
  }

  function hide() {
    overlay.hidden = true;
    pending = null;
  }

  okBtn.addEventListener("click", function () {
    var fn = pending;
    hide();
    if (fn) fn();
  });
  cancelBtn.addEventListener("click", hide);
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) hide();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !overlay.hidden) hide();
  });

  document.addEventListener(
    "click",
    function (e) {
      var el = e.target.closest("[data-confirm]");
      if (!el) return;
      e.preventDefault();
      show(el.getAttribute("data-confirm"), function () {
        if (el.tagName === "A") {
          // A click on the modal's OK button is itself a fresh user gesture,
          // so window.open here is NOT caught by the popup blocker.
          window.open(el.href, el.getAttribute("target") || "_self");
        } else if (el.form) {
          el.form.submit();
        }
      });
    },
    true
  );
})();
