using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Subtegral.DialogueSystem.DataContainers;
using UnityEditor;
using UnityEditor.Experimental.GraphView;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.UIElements;
using Button = UnityEngine.UIElements.Button;

namespace Subtegral.DialogueSystem.Editor
{
    public class StoryGraphView : GraphView
    {
        public readonly Vector2 DefaultNodeSize = new Vector2(200, 150);
        public readonly Vector2 DefaultCommentBlockSize = new Vector2(300, 200);
        public DialogueNode EntryPointNode;
        private NodeSearchWindow _searchWindow;

        public StoryGraphView(StoryGraph editorWindow)
        {
            styleSheets.Add(Resources.Load<StyleSheet>("NarrativeGraph"));
            SetupZoom(ContentZoomer.DefaultMinScale, ContentZoomer.DefaultMaxScale);

            this.AddManipulator(new ContentDragger());
            this.AddManipulator(new SelectionDragger());
            this.AddManipulator(new RectangleSelector());
            this.AddManipulator(new FreehandSelector());

            var grid = new GridBackground();
            Insert(0, grid);
            grid.StretchToParentSize();

            AddElement(GetEntryPointNodeInstance());

            AddSearchWindow(editorWindow);
        }
        private void AddSearchWindow(StoryGraph editorWindow)
        {
            _searchWindow = ScriptableObject.CreateInstance<NodeSearchWindow>();
            _searchWindow.Configure(editorWindow, this);
            nodeCreationRequest = context =>
                SearchWindow.Open(new SearchWindowContext(context.screenMousePosition), _searchWindow);
        }
        public override List<Port> GetCompatiblePorts(Port startPort, NodeAdapter nodeAdapter)
        {
            var compatiblePorts = new List<Port>();
            var startPortView = startPort;

            ports.ForEach((port) =>
            {
                var portView = port;
                if (startPortView != portView && startPortView.node != portView.node)
                    compatiblePorts.Add(port);
            });

            return compatiblePorts;
        }

        public void CreateNewDialogueNode(string nodeName, Vector2 position)
        {
            var tempDialogueNode = new DialogueNode()
            {
                DialogueText = nodeName,
                GUID = Guid.NewGuid().ToString(),
                outputCards = new List<TextField>(),

            };
            AddElement(CreateNode(tempDialogueNode, position));
        }

        public DialogueNode CreateNode(DialogueNode tempDialogueNode, Vector2 position)
        {
            tempDialogueNode.outputPorts = new List<Port>();
            tempDialogueNode.inputPorts = new List<Port>();
            tempDialogueNode.styleSheets.Add(Resources.Load<StyleSheet>("Node"));
            //var inputPort = GetPortInstance(tempDialogueNode, Direction.Input, Port.Capacity.Multi);
            //inputPort.portName = "Response";
            //tempDialogueNode.inputContainer.Add(inputPort);
            //var inputTag = new TextField("inputTag") { value = tempDialogueNode.inputTag };
            //tempDialogueNode.inputContainer.Add(inputTag);
            //inputTag.RegisterValueChangedCallback(evt =>
            //{
            //    tempDialogueNode.inputTag = evt.newValue;
            //    inputPort.name = evt.newValue;
            //});
            //tempDialogueNode.RefreshExpandedState();
            //tempDialogueNode.RefreshPorts();
            tempDialogueNode.SetPosition(new Rect(position,
                DefaultNodeSize)); //To-Do: implement screen center instantiation positioning
            var label = new Label("NpcDialogue");
            var textField = new TextField()
            {
                multiline = true,
            };
            textField.RegisterValueChangedCallback(evt =>
            {
                tempDialogueNode.DialogueText = evt.newValue;
            });
            textField.SetValueWithoutNotify(tempDialogueNode.DialogueText);
            tempDialogueNode.mainContainer.Add(label);
            tempDialogueNode.mainContainer.Add(textField);
            var button = new Button();
            button = new Button(() => { AddInput(tempDialogueNode, ""); })
            {
                text = "Add Input"
            };
            tempDialogueNode.titleContainer.Add(button);
            button = new Button(() => { AddChoice(tempDialogueNode); })
            {
                text = "Add Choice"
            };
            tempDialogueNode.mainContainer.Add(button);
            //if (tempDialogueNode.choiceDatas != null)
            //    foreach (DialogueChoiceData d in tempDialogueNode.choiceDatas)
            //        addChoice(tempDialogueNode, d);
            button = new Button(() => { AddOuput(tempDialogueNode, ""); })
            {
                text = "Add Output"
            };
            tempDialogueNode.mainContainer.Add(button);
            return tempDialogueNode;
        }

        public void AddInput(DialogueNode tempDialogueNode, string v)
        {
            var inputPort = GetPortInstance(tempDialogueNode, Direction.Input, Port.Capacity.Multi);
            inputPort.name = "";
            tempDialogueNode.inputPorts.Add(inputPort);
            tempDialogueNode.inputContainer.Add(inputPort);
            var inputTag = new TextField("") { value = v };
            inputPort.contentContainer.Add(inputTag);
            inputTag.RegisterValueChangedCallback(evt =>
            {
                inputPort.name = evt.newValue;
            });
            var deleteButton = new Button(() => RemoveInput(tempDialogueNode, inputPort))
            {
                text = "X",
                tabIndex = 0
            };
            inputPort.contentContainer.Add(deleteButton);
            tempDialogueNode.RefreshExpandedState();
            tempDialogueNode.RefreshPorts();
            Debug.Log(v);
            inputPort.name = v;
        }

        private void RemoveInput(DialogueNode tempDialogueNode, Port inputPort)
        {
            tempDialogueNode.inputContainer.Remove(inputPort);
            tempDialogueNode.inputPorts.Remove(inputPort);
        }

        private void AddChoice(DialogueNode tempDialogueNode)
        {
            DialogueChoiceData dialogueChoiceData = new DialogueChoiceData();
            if (tempDialogueNode.choiceDatas == null)
                tempDialogueNode.choiceDatas = new List<DialogueChoiceData>();
            tempDialogueNode.choiceDatas.Add(dialogueChoiceData);
            addChoice(tempDialogueNode, dialogueChoiceData);
            //if (tempDialogueNode.choiceDatas == null)
            //    tempDialogueNode.choiceDatas = new List<DialogueChoiceData>();
            //tempDialogueNode.choiceDatas.Add(dialogueChoiceData);
        }

        internal void addChoice(DialogueNode tempDialogueNode, DialogueChoiceData dialogueChoiceData)
        {
            var choice = new TemplateContainer();
            var label = new Label("Choice:");

            // Debug.Log(tempDialogueNode.choiceDatas.Count);
            if (tempDialogueNode.outputCards == null)
                tempDialogueNode.outputCards = new List<TextField>();
            choice.Add(label);
            var generatedPort = GetPortInstance(tempDialogueNode, Direction.Output);

            var portLabel = generatedPort.contentContainer.Q<Label>("type");
            generatedPort.contentContainer.Remove(portLabel);
            tempDialogueNode.outputPorts.Add(generatedPort);
            var deleteButton = new Button(() => removeChoice(tempDialogueNode, dialogueChoiceData, choice, generatedPort))
            {
                text = "X",
                tabIndex = 0,
            };
            var textField = new TextField()
            {
                multiline = true,
                value = dialogueChoiceData.lines
            };
            textField.RegisterValueChangedCallback(evt =>
            {
                dialogueChoiceData.lines = evt.newValue;

            });
            textField.contentContainer.Add(deleteButton);
            choice.Add(generatedPort);

            var tagField = new TextField()
            {
                value = dialogueChoiceData.tag,

            };
            generatedPort.name = dialogueChoiceData.tag;
            tagField.RegisterValueChangedCallback(evt =>
            {
                dialogueChoiceData.tag = evt.newValue;
                generatedPort.name = evt.newValue;
            });
            choice.Add(tagField);
            choice.Add(textField);
            tempDialogueNode.mainContainer.Add(choice);
            tempDialogueNode.RefreshExpandedState();
            tempDialogueNode.RefreshPorts();
        }
        private void removeChoice(DialogueNode tempDialogueNode, DialogueChoiceData dialogueChoiceData, TemplateContainer choice, Port port)
        {
            tempDialogueNode.mainContainer.Remove(choice);
            tempDialogueNode.choiceDatas.Remove(dialogueChoiceData);
            tempDialogueNode.outputPorts.Remove(port);
        }

        public void AddOuput(DialogueNode nodeCache, string input)
        {
            TemplateContainer t = new TemplateContainer();
            var textField = new TextField()
            {
                name = string.Empty,
                value = input,
            };
            if (nodeCache.outputCards == null)
                nodeCache.outputCards = new List<TextField>();
            t.contentContainer.Add(new Label("output:"));
            nodeCache.outputCards.Add(textField);
            var deleteButton = new Button(() => RemoveOutput(nodeCache, t, textField))
            {
                text = "X",
                tabIndex = 0
            };
            textField.contentContainer.Add(deleteButton);
            t.contentContainer.Add(textField);
            nodeCache.mainContainer.Add(t);
            nodeCache.RefreshExpandedState();
        }

        private void RemoveOutput(DialogueNode nodeCache, TemplateContainer t, TextField t2)
        {
            nodeCache.mainContainer.Remove(t);
            nodeCache.RefreshExpandedState();
            nodeCache.outputCards.Remove(t2);
        }

        public void AddChoicePort(DialogueNode nodeCache, string overriddenPortName = "")
        {
            var generatedPort = GetPortInstance(nodeCache, Direction.Output);
            var portLabel = generatedPort.contentContainer.Q<Label>("type");
            generatedPort.contentContainer.Remove(portLabel);

            var outputPortCount = nodeCache.outputContainer.Query("connector").ToList().Count();
            var outputPortName = string.IsNullOrEmpty(overriddenPortName)
                ? $"Option {outputPortCount + 1}"
                : overriddenPortName;
            var textField = new TextField()
            {
                name = string.Empty,
                value = outputPortName,
            };
            var container = new TemplateContainer()
            {

            };
            textField.RegisterValueChangedCallback(evt => generatedPort.portName = evt.newValue);
            ///            generatedPort
            container.contentContainer.Add(new Label() { text = "Output" });
            var deleteButton = new Button(() =>
            {
                RemovePort(nodeCache, generatedPort);
                nodeCache.outputPorts.Remove(generatedPort);
            })
            {
                text = "X"
            };
            container.contentContainer.Add(textField);
            textField.contentContainer.Add(deleteButton);
            generatedPort.contentContainer.Add(container);
            generatedPort.portName = outputPortName;
            nodeCache.outputContainer.Add(generatedPort);
            nodeCache.RefreshPorts();
            nodeCache.RefreshExpandedState();
            if (nodeCache.outputPorts == null)
                nodeCache.outputPorts = new List<Port>();
            nodeCache.outputPorts.Add(generatedPort);
        }

        private void RemovePort(Node node, Port socket)
        {
            var targetEdge = edges.ToList()
                .Where(x => x.output.portName == socket.portName && x.output.node == socket.node);
            if (targetEdge.Any())
            {
                var edge = targetEdge.First();
                edge.input.Disconnect(edge);
                RemoveElement(targetEdge.First());
            }
            node.outputContainer.Remove(socket);
            node.RefreshPorts();
            node.RefreshExpandedState();
        }

        private Port GetPortInstance(DialogueNode node, Direction nodeDirection,
            Port.Capacity capacity = Port.Capacity.Single)
        {
            return node.InstantiatePort(Orientation.Horizontal, nodeDirection, capacity, typeof(string));
        }

        private DialogueNode GetEntryPointNodeInstance()
        {
            var nodeCache = new DialogueNode()
            {
                title = "START",
                GUID = Guid.NewGuid().ToString(),
                DialogueText = "ENTRYPOINT",
                EntyPoint = true
            };

            var generatedPort = GetPortInstance(nodeCache, Direction.Output);
            generatedPort.portName = "Next";
            nodeCache.outputContainer.Add(generatedPort);

            nodeCache.capabilities &= ~Capabilities.Movable;
            nodeCache.capabilities &= ~Capabilities.Deletable;

            nodeCache.RefreshExpandedState();
            nodeCache.RefreshPorts();
            nodeCache.SetPosition(new Rect(100, 200, 100, 150));
            return nodeCache;
        }
    }
}