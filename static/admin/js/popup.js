(() => {
    'use strict';

    const password = $('#password');
    const btn = $('#submit-btn');

    let isBtnDisabled = true;

    password.keyup(() => {
        if (password.val().length >= 8) {
            if (isBtnDisabled) {
                btn.prop('disabled', false);
                isBtnDisabled = false;
            }
        } else {
            if (!isBtnDisabled) {
                btn.prop('disabled', true);
                isBtnDisabled = true;
            }
        }
    });
})();
