!function ($, ckan) {

  $(function () {
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="datepicker"]').datepicker();
  });

  ckan.module('new-resource-form', function ($, _) {
    return {
      initialize: function () {
        var url_bits = window.location.href.split('/');
        var url = window.location.origin+'/dataset/contact/'+url_bits.pop();
        $('#field-image-url').val(url);
        $('#field-name').val('Contact Information');
        $('#field-format').val('contact-link');
      }
    };
  });

}(window.jQuery, this.ckan);
