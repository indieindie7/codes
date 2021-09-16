using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using UnityEditor;
using UnityEditor.Experimental.GraphView;
using UnityEngine;
using Subtegral.DialogueSystem.DataContainers;
using UnityEngine.UIElements;

namespace Subtegral.DialogueSystem.Editor
{
    public class GraphSaveUtility
    {
        private List<Edge> Edges => _graphView.edges.ToList();
        private List<DialogueNode> Nodes => _graphView.nodes.ToList().Cast<DialogueNode>().ToList();

        private List<Group> CommentBlocks =>
            _graphView.graphElements.ToList().Where(x => x is Group).Cast<Group>().ToList();

        private DialogueContainer _dialogueContainer;
        private StoryGraphView _graphView;

        public static GraphSaveUtility GetInstance(StoryGraphView graphView)
        {
            return new GraphSaveUtility
            {
                _graphView = graphView
            };
        }

        public void SaveGraph(string fileName)
        {
            var dialogueContainerObject = ScriptableObject.CreateInstance<DialogueContainer>();
            if (!SaveNodes(fileName, dialogueContainerObject)) return;
            if (!AssetDatabase.IsValidFolder("Assets/Resources"))
                AssetDatabase.CreateFolder("Assets", "Resources");

            UnityEngine.Object loadedAsset = AssetDatabase.LoadAssetAtPath($"Assets/Resources/{fileName}.asset", typeof(DialogueContainer));

            if (loadedAsset == null || !AssetDatabase.Contains(loadedAsset))
            {
                AssetDatabase.CreateAsset(dialogueContainerObject, $"Assets/Resources/{fileName}.asset");
            }
            else
            {
                DialogueContainer container = loadedAsset as DialogueContainer;
                container.NodeLinks = dialogueContainerObject.NodeLinks;
                container.DialogueNodeData = dialogueContainerObject.DialogueNodeData;
                EditorUtility.SetDirty(container);
            }
            AssetDatabase.SaveAssets();
        }

        private bool SaveNodes(string fileName, DialogueContainer dialogueContainerObject)
        {
            //
            //
            if (Edges.Count() > 0)
            {
                Debug.Log(Edges.Count());
                //   return false;
                var connectedSockets = Edges.Where(x => x.input.node != null).ToArray();
                Debug.Log(connectedSockets.Count());
                for (var i = 0; i < connectedSockets.Count(); i++)
                {
                    var outputNode = (connectedSockets[i].output.node as DialogueNode);
                    var inputNode = (connectedSockets[i].input.node as DialogueNode);
                    dialogueContainerObject.NodeLinks.Add(new NodeLinkData
                    {
                        BaseNodeGUID = outputNode.GUID,
                        inputTag = connectedSockets[i].input.name,
                        choiceTag = connectedSockets[i].output.name,
                        TargetNodeGUID = inputNode.GUID
                    });

                }
            }
            foreach (var node in Nodes)//.Where(node => !node.EntyPoint))
                if (!node.EntyPoint)
                {
                    if (node.choiceDatas == null)
                        node.choiceDatas = new List<DialogueChoiceData>();
                    if (node.outputCards == null)
                        node.outputCards = new List<TextField>();
                    //Debug.Log(node.choiceDatas.Count);
                    DialogueChoiceData[] da = new DialogueChoiceData[0];
                    dialogueContainerObject.DialogueNodeData.Add(new DialogueNodeData
                    {
                        NodeGUID = node.GUID,
                        DialogueText = node.DialogueText,
                        outputTags = getOutput(node),
                        choices = node.choiceDatas.ToArray(),
                        inputTags = getInput(node),
                        Position = node.GetPosition().position
                    });
                    //Debug.Log(dialogueContainerObject.DialogueNodeData.Last().choices.Count());
                }
            return true;
        }

        private string[] getInput(DialogueNode node)
        {
            string[] input = new string[node.inputPorts.Count];
            for (int i = 0; i < input.Length; i++)
                input[i] = node.inputPorts[i].name;
            return input;
        }

        private string[] getOutput(DialogueNode node)
        {
            string[] output = new string[node.outputCards.Count];
            for (int i = 0; i < output.Length; i++)
                output[i] = node.outputCards[i].value;
            return output;
        }
        public void LoadNarrative(string fileName)
        {
            _dialogueContainer = Resources.Load<DialogueContainer>(fileName);
            if (_dialogueContainer == null)
            {
                EditorUtility.DisplayDialog("File Not Found", "Target Narrative Data does not exist!", "OK");
                return;
            }
            ClearGraph();
            GenerateDialogueNodes();
            ConnectDialogueNodes();
        }

        /// <summary>
        /// Set Entry point GUID then Get All Nodes, remove all and their edges. Leave only the entrypoint node. (Remove its edge too)
        /// </summary>
        private void ClearGraph()
        {
            //   Debug.Log(Nodes.Count());
            // Nodes.Find(x => x.EntyPoint).GUID = _dialogueContainer.NodeLinks[0].BaseNodeGUID;
            foreach (var perNode in Nodes)
            {
                if (perNode.EntyPoint) continue;
                //   Edges.Where(x => x.input.node == perNode).ToList()
                //     .ForEach(edge => _graphView.RemoveElement(edge));
                _graphView.RemoveElement(perNode);
            }
            foreach (var edges in Edges)
                _graphView.RemoveElement(edges);
        }

        /// <summary>
        /// Create All serialized nodes and assign their guid and dialogue text to them
        /// </summary>
        private void GenerateDialogueNodes()
        {
            foreach (var perNode in _dialogueContainer.DialogueNodeData)
            {
                DialogueNode tempNode = dataExtract(perNode);
                tempNode = _graphView.CreateNode(tempNode, Vector2.zero);
                tempNode.GUID = perNode.NodeGUID;
                _graphView.AddElement(tempNode);
                var nodePorts = _dialogueContainer.NodeLinks.Where(x => x.BaseNodeGUID == perNode.NodeGUID).ToList();
                foreach (string s in perNode.outputTags)
                {
                    _graphView.AddOuput(tempNode, s);
                }
                foreach(string s in perNode.inputTags)
                {
                    _graphView.AddInput(tempNode, s);
                }
                Debug.Log(perNode.choices.Count());
                if(perNode.choices!=null)
                foreach(DialogueChoiceData d in perNode.choices)
                {
                    _graphView.addChoice(tempNode, d);
                }
            }
        }

        private DialogueNode dataExtract(DialogueNodeData perNode)
        {
            DialogueNode d = new DialogueNode();
            if (perNode.choices != null)
                d.choiceDatas = perNode.choices.ToList();
            d.DialogueText = perNode.DialogueText;
            return d;
        }
        private void ConnectDialogueNodes()
        {
            Debug.Log(Nodes.Count);
            for (var i = 0; i < Nodes.Count; i++)
            {
                var k = i; //Prevent access to modified closure
                var connections = _dialogueContainer.NodeLinks.Where(x => x.BaseNodeGUID == Nodes[k].GUID).ToList();
                Debug.Log(connections.Count);
                for (var j = 0; j < connections.Count(); j++)
                {
                    var targetNodeGUID = connections[j].TargetNodeGUID;
                    var targetNode = Nodes.First(x => x.GUID == targetNodeGUID);
                    //     LinkNodesTogether(connections[j].BaseNodeGUID
                    Debug.Log(connections[j].inputTag);
                    foreach (Port p in targetNode.inputPorts)
                        Debug.Log(p.name);
                    LinkNodesTogether(
                        Nodes[i].EntyPoint ?
                            Nodes[i].outputContainer[j].Q<Port>() :
                            Nodes[i].outputPorts[j],
                        (Port)targetNode.inputPorts[targetNode.inputPorts.IndexOf(targetNode.inputPorts.Find(x => x.name== connections[j].inputTag))]);
                    targetNode.SetPosition(new Rect(
                        _dialogueContainer.DialogueNodeData.First(x => x.NodeGUID == targetNodeGUID).Position,
                        _graphView.DefaultNodeSize));
                }
            }
        }

        private void LinkNodesTogether(Port outputSocket, Port inputSocket)
        {
            var tempEdge = new Edge()
            {
                output = outputSocket,
                input = inputSocket
            };
            tempEdge?.input.Connect(tempEdge);
            tempEdge?.output.Connect(tempEdge);
            _graphView.Add(tempEdge);
        }
    }
}