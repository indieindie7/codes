using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
//using UnityEngine.EventSystems;
namespace playerInventory
{
    public class PlayerInventory : MonoBehaviour
    {
        public float toolbarHeight, spotSize;
        public Image prefabSpot, prefabBackground, prefabToolBar;
        public Item prefabItem;
        public Canvas invCanvas;



        // public Sprite[] sprites;
        public Transform ItemsTransform, worldItemsTransform;
        // internal Item beingDragged; 
        #region object Dragging
        Item draggedObject;
        Vector3 mousePos;
        Vector3 originalPos, originalRotation;
        private void Start()
        {
            setVisual();
        }
        internal void startDraggin(Item obj)
        {
            obj.transform.SetAsLastSibling();
            draggedObject = obj;
            draggedObject.GetComponent<Image>().raycastTarget = false;
            if (draggedObject.transform.parent.GetComponent<SpecialSpot>() != null)
                draggedObject.transform.parent.GetComponent<Image>().raycastTarget = true;
            //      
            originalPos = draggedObject.transform.position;
            originalRotation = draggedObject.transform.eulerAngles;
            mousePos = Input.mousePosition;
        }

        internal void setVisual()
        {
            draggedObject = null;
            int childs = ItemsTransform.childCount;
            for (int i = childs - 1; i >= 0; i--)
            {
                GameObject.Destroy(ItemsTransform.GetChild(i).gameObject);
            }
            foreach (SpecialSpot s in spots)
            {
                s.GetComponent<Image>().enabled = Cursor.visible;
                if (s.Item != null)
                {
                    foreach (Transform t in s.Item.transform)
                        t.gameObject.SetActive(Cursor.visible);
                    //if(s.filterTag==tip)
                    s.Item.gameObject.SetActive(Cursor.visible);
                }
            }
        }
        SpecialSpot currentSpecialSpot;
        internal void mouseSpecialExit(SpecialSpot specialSpot)
        {
            if (currentSpecialSpot == specialSpot)
                currentSpecialSpot = null;
        }
        internal void mouseSpecialEnter(SpecialSpot specialSpot)
        {
            currentSpecialSpot = specialSpot;
        }
        void dragUpdate()
        {
            if (draggedObject == null)
                return;
            draggedObject.transform.position += Input.mousePosition - mousePos;
            mousePos = Input.mousePosition;
            if (Input.GetKeyDown(KeyCode.R) && draggedObject.GetComponent<Item>() != null)
                draggedObject.GetComponent<Item>().rotate();
            if (Input.GetMouseButtonUp(0))
                stopDraggin();
        }
        Item currentStorage;
        internal void mouseStorageExit(Item Item)
        {
            if (currentStorage == Item)
                currentStorage = null;
        }
        internal void mouseStorageEnter(Item Item)
        {
            currentStorage = Item;
        }

        private void OnDrawGizmos()
        {
        }
        bool ItemCanfit(Item toFit, Item whereToFit)
        {
            Debug.Log(toFit + " in " + whereToFit);
            Dictionary<ItemSpot, ItemSpot> targetSpots = new Dictionary<ItemSpot, ItemSpot>();
            foreach (ItemSpot iSpotFrom in toFit.mySpots)
            {
                ItemSpot closest = iSpotFrom;
                float distance = spotSize;
                foreach (ItemSpot iSpotWhere in whereToFit.mySpots)
                {
                    float d =
                        Vector3.Distance(iSpotFrom.transform.position, iSpotWhere.transform.position);
                    if (distance >= d)
                    {
                        distance = d;
                        closest = iSpotWhere;
                    }
                }
                if (closest != iSpotFrom)
                    targetSpots.Add(iSpotFrom, closest);
            }
            if (targetSpots.Count < toFit.mySpots.Count) return false;
            Debug.Log(targetSpots.Count + " " + spotSize);
            foreach (ItemSpot iSpotWhere in whereToFit.mySpots)
                if (iSpotWhere.Item == toFit)
                    iSpotWhere.Item = null;
            if (targetSpots.Count == 0) return false;
            KeyValuePair<ItemSpot, ItemSpot> k = targetSpots.First();
            Vector3 movDir = k.Value.transform.position - k.Key.transform.position;
            toFit.transform.position += movDir;
            if (toFit.transform.parent.GetComponent<ItemSpot>() != null)
            {
                toFit.transform.parent.GetComponent<ItemSpot>().Item = null;
                toFit.transform.parent.GetComponent<Image>().raycastTarget = true;
            }
            cleanParents(toFit);
            toFit.transform.SetParent(whereToFit.transform);
            foreach (ItemSpot kV in targetSpots.Values)
                kV.Item = toFit;
            whereToFit.origin.ItemHelds.Add(toFit);
            return true;
        }
        void cleanParents(Item toClean)
        {
            //if (toClean.transform.parent.GetComponent<Image>() != null)
            //    toClean.transform.parent.GetComponent<Image>().raycastTarget = true;
            if (toClean.transform.parent.GetComponent<SpecialSpot>() != null)
                toClean.transform.parent.GetComponent<SpecialSpot>().Item = null;
            if (toClean.transform.parent.GetComponent<Item>() != null)
            {
                Item storage = toClean.transform.parent.GetComponent<Item>();
                if (storage.origin.canStore)
                {
                    foreach (ItemSpot t in storage.mySpots)
                        if (t.Item == toClean)
                            t.Item = null;
                    storage.origin.ItemHelds.Remove(toClean);
                }
            }

        }
        //  bool isInside = false;
        //internal void insideInventory(bool v)
        //{
        //    isInside = v;
        //    Debug.Log("isInside:" + v);https://www.youtube.com/watch?v=WWjLkNRp_eM
        //}
        internal void stopDraggin()
        {
            bool fail = false;
            if (currentSpecialSpot != null && draggedObject.GetComponent<Item>() != null &&
                (currentSpecialSpot.Item == null || currentSpecialSpot.Item == draggedObject.GetComponent<Item>()) && canPlace())
            {
                cleanParents(draggedObject);
                currentSpecialSpot.Item = draggedObject;
                draggedObject.transform.SetParent(currentSpecialSpot.transform);
                draggedObject.transform.position = currentSpecialSpot.transform.position;
            }
            else
            {
                fail = true;
            }
            if (currentStorage != null)
            {
                if (ItemCanfit(draggedObject, currentStorage))
                {
                    fail = false;
                }
            }
            draggedObject.GetComponent<Image>().raycastTarget = true;
            foreach (Transform t in draggedObject.transform) t.GetComponent<Image>().raycastTarget = true;
            if (!fail)
            {
                if (currentStorage != null)
                {
                    //inside storage
                    draggedObject.origin.gameObject.SetActive(false);
                    draggedObject.transform.SetParent(currentStorage.transform);
                }
                else
                {
                    ///special
                    draggedObject.origin.gameObject.SetActive(true);
                    draggedObject.origin.transform.SetParent(currentSpecialSpot.objectTransform.transform);
                    draggedObject.origin.transform.position = currentSpecialSpot.objectTransform.transform.position;
                    draggedObject.origin.transform.rotation = currentSpecialSpot.objectTransform.transform.rotation;
                }
                draggedObject.origin.GetComponent<Rigidbody>().isKinematic = true;
            }
            else
            {
                ///on world
                draggedObject.origin.transform.position = GameObject.Find("base").transform.position + GameObject.Find("AxisX").transform.right * 0.2f;
                draggedObject.origin.gameObject.SetActive(true);
                draggedObject.transform.SetParent(ItemsTransform);
                draggedObject.origin.transform.SetParent(worldItemsTransform);
                draggedObject.origin.GetComponent<Rigidbody>().isKinematic = false;

            }
            draggedObject = null;
        }


        private bool canPlace()
        {
            //currentSpecialSpot.filterTag==spotPlace.hand || 
            return draggedObject.origin.spot == currentSpecialSpot.filterTag;
        }

        #endregion
        Vector3 spot(Vector2Int pos, Transform t)
        {
            return t.position + new Vector3((pos.x) * prefabSpot.rectTransform.rect.width, (-pos.y) * prefabSpot.rectTransform.rect.height);
        }
        public SpecialSpot[] spots;
        void Update()
        {
            if (!Cursor.visible) return;
            foreach (SpecialSpot s in spots)
                s.transform.position = Camera.main.WorldToScreenPoint(s.objectTransform.position);
            dragUpdate();
        }
        /// INSTANTIATORS
        #region generation of objects
        Vector3 imagePosition(Vector2Int pos)
        {
            return Input.mousePosition + new Vector3((float)pos.x / 2, -(float)pos.y / 2) * spotSize;
        }
        void ItemVisualToggle(Item Item, bool h)
        {
            Item.GetComponent<Image>().enabled = h;
            Item.GetComponent<Image>().raycastTarget = h;
            foreach (Transform t in Item.transform)
                if (t.GetComponent<Image>() != null)
                    t.GetComponent<Image>().enabled = h;
        }
        internal void insantiateGUI(Item ItemStorage)
        {
            Debug.Log(ItemStorage.name);
            if (!invCanvas.gameObject.activeSelf) return;
            if (ItemStorage.transform.eulerAngles != Vector3.zero) return;
            ItemStorage.isShowing = true;
            ItemStorage.GetComponent<Image>().color = new Color(1, 1, 1, 0.5f);
            if (ItemStorage.origin.ItemHelds == null)
                ItemStorage.origin.ItemHelds = new List<Item>();
            foreach (Item it in ItemStorage.origin.ItemHelds)
                ItemVisualToggle(it, true);
            foreach (ItemSpot iS in ItemStorage.mySpots)
                iS.GetComponent<Image>().enabled = true;
            ///toolbar add
            Image cd = Instantiate(prefabToolBar,
                    Input.mousePosition,
                      Quaternion.identity, ItemStorage.transform);
            cd.rectTransform.localPosition =
                new Vector3(0, (((float)ItemStorage.origin.size.y) / 2) * spotSize + toolbarHeight / 2);
            cd.rectTransform.sizeDelta = new Vector2((float)ItemStorage.origin.size.x * spotSize, toolbarHeight);
            cd.transform.GetChild(1).GetComponent<Button>().onClick.AddListener(() =>
            {
                ItemStorage.isShowing = false;
                ItemStorage.GetComponent<Image>().color = Color.white;
                foreach (Item it in ItemStorage.origin.ItemHelds)
                    ItemVisualToggle(it, false);
                foreach (ItemSpot iS in ItemStorage.mySpots)
                    iS.GetComponent<Image>().enabled = false;
                Destroy(cd.gameObject);
            });
        }
        internal void generateItem(ItemLevel baseData)
        {
            if (!invCanvas.gameObject.activeSelf || baseData.imageVersion != null) return;
            Vector2Int size = new Vector2Int(UnityEngine.Random.Range(1, 6), UnityEngine.Random.Range(1, 6));
            Item c = Instantiate(prefabItem, imagePosition(size), Quaternion.identity, ItemsTransform);//.AddComponent<Item>();
            c.origin = baseData;
            // c.setData(baseData);
            // c.size = baseData.myData.size;
            c.GetComponent<RectTransform>().sizeDelta =
                new Vector2((float)baseData.size.x, baseData.size.y) * spotSize;
            //c.transform.GetChild(0).GetComponent<RectTransform>().sizeDelta =
            //    new Vector2((float)baseData.size.x, baseData.size.y) * spotSize;
            //.GetComponent<Image>().sprite = sprite;
            c.mySpots = new List<ItemSpot>();
            Instantiate(prefabBackground, imagePosition(size), Quaternion.identity, c.transform)
                .GetComponent<RectTransform>().sizeDelta =
                new Vector2((float)baseData.size.x, baseData.size.y) * spotSize;
            //backGroundSet(c);
            for (int x = 0; x < baseData.size.x; x++)
                for (int y = 0; y < baseData.size.y; y++)
                {
                    Image cd = Instantiate(prefabSpot, Input.mousePosition, Quaternion.identity, c.transform);
                    cd.rectTransform.localPosition =
                        new Vector3(x + 0.5f - ((float)baseData.size.x) / 2, y + 0.5f - ((float)baseData.size.y) / 2) * spotSize;
                    // , y + 0.5f ) * spotSize;
                    cd.rectTransform.sizeDelta = Vector2.one * spotSize;
                    cd.color = new Color(1, 1, 1, c.origin.canStore ? 0.25f : 0.01f);
                    c.mySpots.Add(cd.GetComponent<ItemSpot>());
                    cd.enabled = false;
                }
            baseData.imageVersion = c;
            //   if (c.myData.canStore) c.myData.ItemHelds = new List<Item>();
        }
        #endregion
    }
}