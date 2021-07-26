$(() => {
    'use strict';
    
    const password = $('#password');
    const btn = $('#submit-btn');
    const updateFirmwareBtn = $('#update-firmware-btn');
    let isBtnDisabled = true;
    
    $(".modal").on('shown.bs.modal', () => {
        $('#password').focus();
    });
        
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
});


