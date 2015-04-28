(function ($) {
    $.fn.logToggle = function (options) {

        var settings = $.extend({
            hide: true
        }, options);

        function togglerHandler(el, hide) {
            el.find('span')
                .text(hide ? "Afficher" : "Cacher");
            el.find('i')
                .toggleClass('fa-caret-down', !hide)
                .toggleClass('fa-caret-right', hide);
        }

        return this.each(function () {
            var toggler = $(this),
                targetref = toggler.attr('data-target'),
                target = $(targetref);
            if (!target) {
                console.warning("Target element", targetref, "of toggler", toggler, "does not exist");
                return;
            }
            togglerHandler(toggler, settings.hide);
            if (settings.hide) {
                target.hide();
            }
            toggler.click(function () {
                var hidden = target.is(':hidden');
                togglerHandler(toggler, !hidden);
                target.slideToggle('fast');
            });
        });

    };

    $(function() {
        // automagically find log togglers
        $('[data-role="toggler"]').logToggle({hide: true});
    });

})(jQuery);