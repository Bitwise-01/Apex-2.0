$(() => {
    'use strict';

    const submitBtn = $('#submit-btn');
    const passwordInput = $('#password');
    const msg = $('#msg');

    let updating = false; 

    // Shadow 
    const shadowNormal = 'rgb(0 123 255 / 25%)';
    const shadowInvalid =  'rgb(220 53 69 / 25%)';
    const shadowValid = 'rgb(40 167 69 / 50%)';

    submitBtn.click(() => updateFirmware());

    $('#update-form').submit((e) => {
        e.preventDefault();
        updateFirmware()
    });

    $(document).on('focus', '#password', () => {
        updatePasswordInputShadowColor(shadowNormal);
    });
    
    
    const updatePasswordInputShadowColor = (color) => {
        $('#password').css({'border-color': color, 'box-shadow': `0 0 0 0.2rem ${color}`})
    };


    const hideSubmitBtn = () => {
        $('#submit-btn').hide(); 
        $('#loader').show(); 
    }; 

    const showSubmitBtn = () => {
        $('#submit-btn').show(); 
        $('#loader').hide(); 
    }; 

    const updateFirmware = () => {
        if (updating) {
            return; 
        }

        $('#password').trigger('blur');
        
        msg.hide();
        msg.removeClass('text-danger');
        msg.removeClass('text-success');
        
        const password = passwordInput.val();
        
        if (password.length < 8) {
            msg.text('Password must be at least 8 characters in length');
            msg.addClass('text-danger');
            msg.show();
            return; 
        }
        
        hideSubmitBtn();

        $.ajax({
            type: 'POST',
            url: '/api/v1/router/update-firmware',
            data: { password: password },
        }).done((resp) => {
            setTimeout(() => {
                msg.addClass(resp.status === 1 ? 'text-success' : 'text-danger');
                msg.text(resp.msg);
                msg.show();
                
                updating = resp.status; 
                resp.status !== 1 && showSubmitBtn();
                updatePasswordInputShadowColor(resp.status ? shadowValid : shadowInvalid);
            }, 512);
        });
    } 
});
