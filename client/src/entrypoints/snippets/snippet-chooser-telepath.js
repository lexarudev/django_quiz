class SnippetChooser {
  constructor(html, idForLabel, model) {
    this.html = html;
    this.idForLabel = idForLabel;
    this.model = model;
  }

  render(placeholder, name, id, initialState) {
    const html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
    // eslint-disable-next-line no-param-reassign
    placeholder.outerHTML = html;
    /* the chooser object returned by createImageChooser also serves as the JS widget representation */
    // eslint-disable-next-line no-undef
    const chooser = createSnippetChooser(id, this.model);
    chooser.setState(initialState);
    return chooser;
  }
}
window.telepath.register('wagtail.snippets.widgets.SnippetChooser', SnippetChooser);
