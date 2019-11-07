export interface ITemplateOptions extends AngularFormly.ITemplateOptions {
  trueValue?: any;
  falseValue?: any;
  appendToBody?: boolean;
  refresh?: Function;
  clearEnabled?: boolean;
  optionsFunction?: Function;
}
export interface IFieldObject extends AngularFormly.IFieldObject {
  templateOptions?: ITemplateOptions;
}
export interface IFieldGroup extends AngularFormly.IFieldGroup {
  templateOptions?: ITemplateOptions;
}
