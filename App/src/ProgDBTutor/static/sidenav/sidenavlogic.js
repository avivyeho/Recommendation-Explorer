// Pretty sure that is not how Boostrap should be used but it is working :shrug
$(document).ready(function () {
    $('#sidenav-toggle-button').click(function () {
        $(this).toggleClass('open');
        if ($('#sidenav').hasClass('d-none d-md-block')) {
            $('#sidenav').toggleClass('d-none d-md-block');
            $('#sidenav').toggleClass('col-sm-12');
        } else {
            $('#sidenav').toggleClass('d-none d-md-block');
            $('#sidenav').toggleClass('col-sm-12');
        }
    });
});
