// Saves what "Decidir" decided in the workflow's static data (kept only by
// production executions): the last 50 action ids, and the dispatched cards.
const data = $getWorkflowStaticData('global');
const input = $('Montar entrada').item.json;
const decision = $json;

if (decision.reason !== 'duplicate') {
  data.seenActionIds = [...input.seenActionIds, input.action.id].slice(-50);
}
const dispatched = [...input.dispatched];
if (decision.dispatch && !dispatched.includes(decision.dispatch)) dispatched.push(decision.dispatch);
data.dispatched = dispatched;

return { json: { ...decision, cardId: input.action.cardId } };
