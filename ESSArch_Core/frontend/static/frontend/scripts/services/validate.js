const validate = () => {
  return {
    message: {
      minlength: 'This value is not long enough.',
      maxlength: 'This value is too long',
      email: 'A properly formatted email address is required.',
      required: 'This field is required.',
    },
    more_messages: {
      demo: {
        required: 'Here is a sample alternative required message.',
      },
    },
    check_more_messages: function (name, error) {
      return (this.more_messages[name] || [])[error] || null;
    },
    validation_messages: function (field, form, error_bin) {
      const messages = [];
      for (const e in form[field].$error) {
        if (form[field].$error[e]) {
          const special_message = this.check_more_messages(field, e);
          if (special_message) {
            messages.push(special_message);
          } else if (this.message[e]) {
            messages.push(this.message[e]);
          } else {
            messages.push('Error: ' + e);
          }
        }
      }
      const deduped_messages = [];
      angular.forEach(messages, function (el, i) {
        if (deduped_messages.indexOf(el) === -1) deduped_messages.push(el);
      });
      if (error_bin) {
        error_bin[field] = deduped_messages;
      }
    },
    form_validation: function (form, error_bin) {
      for (const field in form) {
        if (field.substr(0, 1) != '$') {
          this.validation_messages(field, form, error_bin);
        }
      }
    },
  };
};

export default validate;
