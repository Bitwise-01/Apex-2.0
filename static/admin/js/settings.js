(() => {
    'use strict';

    const resp = $('#resp');
    const errors = $('#errors');
    const updates = $('#updates');

    let isSaving = false;

    $('#save-changes').click(() => {
        saveChanges();
    });

    const saveChanges = () => {
        if (isSaving) {
            return;
        }

        let username = $('#username').val();
        let currentPassword = $('#current-password').val();
        let newPassword = $('#new-password').val();
        let confirmPassword = $('#confirm-password').val();

        if (username.trim().length === 0 && currentPassword.trim().length === 0) {
            return;
        }

        isSaving = true;
        $('#save-changes').prop('disabled', true);

        let data = {
            username: username,
            currentPassword: currentPassword,
            newPassword: newPassword,
            confirmPassword: confirmPassword,
        };

        errors.empty();
        updates.empty();
        updates.append('<div class="spinner-grow text-primary" role="status"></div>');

        $.ajax({
            type: 'POST',
            traditional: true,
            url: `/${config.admin_url_prefix}/settings/account/update`,
            data: data,
        }).done((r) => {
            updates.empty();

            r['value']['updates'].forEach((msg) => {
                updates.append(`<p class="text-success">${msg}</p>`);
            });

            r['value']['errors'].forEach((msg) => {
                errors.append(`<p class="text-danger">${msg}</p>`);
            });

            isSaving = false;
            $('#save-changes').prop('disabled', false);
        });
    };
})();
