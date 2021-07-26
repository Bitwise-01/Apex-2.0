$(() => {
    'use strict';
    
    const SIDEBAR_MENU_WIDTH = '210px';
    let isSidebarActive = false;
    
    $('body').click(() => {
        if (isSidebarActive) {
            $('.sidebar').css({ width: 0 });
            isSidebarActive = false;
        }
    });
    
    $('.sidebar-toggle').click((e) => {
        $('.sidebar').css({ width: !isSidebarActive ? SIDEBAR_MENU_WIDTH : 0 });
        isSidebarActive = !isSidebarActive;
        e.stopPropagation();
    });
});
