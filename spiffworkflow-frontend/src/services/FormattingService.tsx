import DateAndTimeService from './DateAndTimeService';

const spiffFormatFunctions: { [key: string]: Function } = {
  convert_seconds_to_date_time_for_display: DateAndTimeService.formatDateTime,
  convert_seconds_to_duration_for_display:
    DateAndTimeService.formatDurationForDisplay,
};

const checkForSpiffFormats = (markdown: string) => {
  const replacer = (
    match: string,
    spiffFormatFunctionName: string,
    originalValue: string,
    otherArgs: string
  ) => {
    console.log(`otherArgs:${otherArgs}:`);
    if (spiffFormatFunctionName in spiffFormatFunctions) {
      return spiffFormatFunctions[spiffFormatFunctionName](
        undefined,
        originalValue
      );
    }
    console.warn(
      `attempted: ${match}, but ${spiffFormatFunctionName} is not a valid conversion function`
    );

    return match;
  };
  return markdown.replaceAll(
    /SPIFF_FORMAT:::(\w+)\(([^,)]+)([^)]*)\)/g,
    replacer
  );
};

const FormattingService = {
  checkForSpiffFormats,
};

export default FormattingService;
