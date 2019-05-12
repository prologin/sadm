django.jQuery = $;
django.jQuery(document).ready(function() {
    var auto_add_toggle = function() {
        if (django.jQuery('#id_auto_add').is(':checked')) {
            django.jQuery('#id_auto_add_deadline').removeAttr('disabled');
            django.jQuery('#id_auto_add_staff').removeAttr('disabled');
        } else {
            django.jQuery('#id_auto_add_deadline').attr('disabled', '');
            django.jQuery('#id_auto_add_staff').attr('disabled', '');
        }
    };
    auto_add_toggle();
    django.jQuery("#id_auto_add").click(auto_add_toggle);
});
