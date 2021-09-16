using System;
using System.Linq;

namespace Subtegral.DialogueSystem.DataContainers
{
    [Serializable]
    public class NodeLinkData
    {
        public string BaseNodeGUID,inputTag,choiceTag,TargetNodeGUID;
    }
}