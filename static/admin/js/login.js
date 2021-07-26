(() => {
    'use strict';

    const errorMsg = $('#error-msg');
    const username = $('#username');
    const password = $('#password');

    $('form').submit((e) => {
        e.preventDefault();

        if (username.val().length <= 0 || password.val().length <= 0) {
            return;
        }

        $.ajax({
            type: 'POST',
            // url: '/apex/',
            url: `/${config.admin_url_prefix}/`,
            data: { username: username.val(), password: password.val() },
        }).done((resp) => {
            if (!resp['isAuthenticated']) {
                password.val('');
                errorMsg.text(resp['msg']);
            } else {
                window.location.href = '/';
            }
        });
    });
})();
