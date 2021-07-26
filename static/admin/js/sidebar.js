(() => {
    'use strict';

    const sidebar = $('.sidebar');
    const SIDEBAR_MENU_WIDTH = '210px';
    let isSidebarActive = false;

    $('body').click(() => {
        if (isSidebarActive) {
            sidebar.css({ width: 0 });
            isSidebarActive = false;   
        }
    });

    const rapidPass = () => {
        // close the sidebar faster than normal // 
        
        const defaultTransitionValue = sidebar.css('transition');

        sidebar.css({ transition: '0s' });
        sidebar.css({ width: 0 });
        isSidebarActive = false;

        let n = 300;

        while ((sidebar.css('width') != '0px') && n > 0) {
            n -= 1;
        }

        // reset speed 
        sidebar.css({ transition: defaultTransitionValue });
    }

    $('.rapid-pass').click((e) => {
        rapidPass();
    });

    $('.sidebar-toggle').click((e) => {
        sidebar.css({ width: !isSidebarActive ? SIDEBAR_MENU_WIDTH : 0 });
        isSidebarActive = !isSidebarActive;
        e.stopPropagation();
    });
})();
