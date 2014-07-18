$(function() {
    "use strict";

    $('.image-url-generator').each(function() {
        var $this = $(this);
        var $form = $this.find('form');
        var $filterMethodField = $form.find('select#id_filter_method');
        var $widthField = $form.find('input#id_width');
        var $heightField = $form.find('input#id_height');
        var $result = $this.find('#result-url');
        var $loadingMask = $this.find('.loading-mask')
        var $preview = $this.find('img.preview');
        var $sizeNote = $('#note-size')

        var generatorUrl = $this.data('generatorUrl');

        function formChangeHandler() {
            var filterSpec = $filterMethodField.val();

            $loadingMask.addClass('loading');

            if (filterSpec == 'original') {
                $widthField.prop('disabled', true);
                $heightField.prop('disabled', true);
            } else if (filterSpec == 'width') {
                $widthField.prop('disabled', false);
                $heightField.prop('disabled', true);
                filterSpec += '-' + $widthField.val();
            } else if (filterSpec == 'height') {
                $widthField.prop('disabled', true);
                $heightField.prop('disabled', false);
                filterSpec += '-' + $heightField.val();
            } else if (filterSpec == 'min' || filterSpec == 'max' || filterSpec == 'fill') {
                $widthField.prop('disabled', false);
                $heightField.prop('disabled', false);
                filterSpec += '-' + $widthField.val() + 'x' + $heightField.val();
            }

            // Display note about scaled down images if image is large
            if($widthField.val() > $(window).width()){
                $sizeNote.show();
            }else{
                $sizeNote.hide();
            }

            // Fields with width and height
            $.getJSON(generatorUrl.replace('__filterspec__', filterSpec))
                .done(function(data) {
                    $result.val(data['url']);
                    $preview.attr('src', data['url']);
                    $loadingMask.removeClass('loading');
                })
                .fail(function(data) {
                    $result.val(data.responseJSON['error']);
                    $preview.attr('src', '');
                    $loadingMask.removeClass('loading');
                });
        }

        $form.change($.debounce(500, formChangeHandler));
        $form.keyup($.debounce(500, formChangeHandler));
        formChangeHandler();

        // When the user clicks the URL, automatically select the whole thing (for easier copying)
        $result.click(function() {
            $(this).select();
        });
    });
});
