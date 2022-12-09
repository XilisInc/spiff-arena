import {
  ComboBox,
  // @ts-ignore
} from '@carbon/react';
import { truncateString } from '../helpers';
import { ProcessGroupLite, ProcessModel } from '../interfaces';

type OwnProps = {
  onChange: (..._args: any[]) => any;
  processModels: ProcessModel[];
  selectedItem?: ProcessModel | null;
  titleText?: string;
};

export default function ProcessModelSearch({
  processModels,
  selectedItem,
  onChange,
  titleText = 'Process model',
}: OwnProps) {
  const getParentGroupsDisplayName = (processModel: ProcessModel) => {
    if (processModel.parent_groups) {
      return processModel.parent_groups
        .map((parentGroup: ProcessGroupLite) => {
          return parentGroup.display_name;
        })
        .join(' ');
    }
    return '';
  };

  const shouldFilterProcessModel = (options: any) => {
    const processModel: ProcessModel = options.item;
    const { inputValue } = options;
    return `${processModel.id} (${getParentGroupsDisplayName(processModel)} ${
      processModel.display_name
    })`.includes(inputValue);
  };
  return (
    <ComboBox
      onChange={onChange}
      id="process-model-select"
      data-qa="process-model-selection"
      items={processModels}
      itemToString={(processModel: ProcessModel) => {
        if (processModel) {
          return `${processModel.id} (${truncateString(
            processModel.display_name,
            75
          )})`;
        }
        return null;
      }}
      shouldFilterItem={shouldFilterProcessModel}
      placeholder="Choose a process model"
      titleText={titleText}
      selectedItem={selectedItem}
    />
  );
}
