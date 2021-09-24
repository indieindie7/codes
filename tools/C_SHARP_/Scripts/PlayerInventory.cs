using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
//using UnityEngine.EventSystems;

public class PlayerInventory : MonoBehaviour
{
    public float toolbarHeight, spotSize;
    public Image prefabSpot, prefabBackground, prefabToolBar;
    public Item prefabItem, prefabBag;
    public Canvas invCanvas;
    public Sprite[] sprites;
    public Transform canvasInventory, containersTransform, itemsTransform;
    // internal Item beingDragged;
    #region object Dragging
    Item draggedObject;
    Vector3 mousePos;
    Vector3 originalPos, originalRotation;
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
    internal void mouseStorageExit(Item item)
    {
        if (currentStorage == item)
            currentStorage = null;
    }
    internal void mouseStorageEnter(Item item)
    {
        currentStorage = item;
    }

    private void OnDrawGizmos()
    {
    }
    bool itemCanfit(Item toFit, Item whereToFit)
    {
        Debug.Log(toFit + " in " + whereToFit);
        Dictionary<ItemSpot, ItemSpot> targetSpots = new Dictionary<ItemSpot, ItemSpot>();
        // Debug.Log(toFit.mySpots.Count + " " + whereToFit.mySpots.Count);
        // Debug.Log(GetComponent<Camera>().ScreenToWorldPoint(toFit.transform.position) + "" + GetComponent<Camera>().ScreenToWorldPoint(whereToFit.transform.position));
        // Debug.Log(Vector3.Distance(toFit.GetComponent<RectTransform>().position, whereToFit.GetComponent<RectTransform>().position));
        // Debug.Log(Vector3.Distance(toFit.transform.position, whereToFit.transform.position));
        //float smallest = Mathf.Infinity;
        foreach (ItemSpot iSpotFrom in toFit.mySpots)
        {
            ItemSpot closest = iSpotFrom;
            float distance = spotSize;
            //Debug.Log(iSpotFrom.name + "" + iSpotFrom.transform.position);
            foreach (ItemSpot iSpotWhere in whereToFit.mySpots)
            {
                float d =
                    Vector3.Distance(iSpotFrom.transform.position, iSpotWhere.transform.position);
                if (distance >= d)
                {
                    distance = d;
                    closest = iSpotWhere;
                }
                // Debug.Log(iSpotWhere.name + "" + iSpotWhere.transform.position + "" + d);
            }
            // Debug.Log(distance);
            if (closest != iSpotFrom)
                targetSpots.Add(iSpotFrom, closest);
        }
        if (targetSpots.Count < toFit.mySpots.Count) return false;
        Debug.Log(targetSpots.Count + " " + spotSize);
        foreach (ItemSpot iSpotWhere in whereToFit.mySpots)
            if (iSpotWhere.item == toFit)
                iSpotWhere.item = null;
        if (targetSpots.Count == 0) return false;
        KeyValuePair<ItemSpot, ItemSpot> k = targetSpots.First();
        Vector3 movDir = k.Value.transform.position - k.Key.transform.position;
        toFit.transform.position += movDir;
        if (toFit.transform.parent.GetComponent<ItemSpot>() != null)
        {
            toFit.transform.parent.GetComponent<ItemSpot>().item = null;
            toFit.transform.parent.GetComponent<Image>().raycastTarget = true;
        }
        cleanParents(toFit);
        toFit.transform.SetParent(whereToFit.transform);
        foreach (ItemSpot kV in targetSpots.Values)
            kV.item = toFit;
        whereToFit.itemHelds.Add(toFit);
        return true;
    }
    void cleanParents(Item toClean)
    {
        if (toClean.transform.parent.GetComponent<Image>() != null)
            toClean.transform.parent.GetComponent<Image>().raycastTarget = true;
        if (toClean.transform.parent.GetComponent<SpecialSpot>() != null)
            toClean.transform.parent.GetComponent<SpecialSpot>().item = null;
        if (toClean.transform.parent.GetComponent<Item>() != null)
        {
            Item storage = toClean.transform.parent.GetComponent<Item>();
            if (storage.canStore)
            {
                foreach (ItemSpot t in storage.mySpots)
                    if (t.item == toClean)
                        t.item = null;
                storage.itemHelds.Remove(toClean);
            }
        }
    }

    internal void stopDraggin()
    {
        bool fail = false;
        if (currentSpecialSpot != null && draggedObject.GetComponent<Item>() != null &&
            (currentSpecialSpot.item == null || currentSpecialSpot.item == draggedObject.GetComponent<Item>()))
        {
            cleanParents(draggedObject);
            currentSpecialSpot.item = draggedObject;
            draggedObject.transform.SetParent(currentSpecialSpot.transform);
            draggedObject.transform.position = currentSpecialSpot.transform.position;
            currentSpecialSpot.GetComponent<Image>().raycastTarget = false;
        }
        else
        {
            fail = true;
        }
        if (currentStorage != null)
        {
            if (itemCanfit(draggedObject, currentStorage))
            {
                fail = false;
            }
        }
        if (fail)
            objectReturn();
        draggedObject.GetComponent<Image>().raycastTarget = true;
        if (draggedObject.transform.parent.GetComponent<Image>() != null)
            draggedObject.transform.parent.GetComponent<Image>().raycastTarget = false;
        foreach (Transform t in draggedObject.transform) t.GetComponent<Image>().raycastTarget = true;
        draggedObject = null;
    }
    void objectReturn()
    {
        draggedObject.transform.position = originalPos;
        draggedObject.transform.eulerAngles = originalRotation;
    }
    #endregion
    Vector3 spot(Vector2Int pos, Transform t)
    {
        return t.position + new Vector3((pos.x) * prefabSpot.rectTransform.rect.width, (-pos.y) * prefabSpot.rectTransform.rect.height);
    }
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Tab))
            invCanvas.gameObject.SetActive(!invCanvas.gameObject.activeSelf);
        if (Input.GetKeyDown(KeyCode.F))
            generateItem(prefabItem);
        if (Input.GetKeyDown(KeyCode.Q))
            generateItem(prefabBag);
        dragUpdate();
    }
    /// INSTANTIATORS
    #region generation of objects
    Vector3 imagePosition(Vector2Int pos)
    {
        return Input.mousePosition + new Vector3((float)pos.x / 2, -(float)pos.y / 2) * spotSize;
    }
    void itemVisualToggle(Item item, bool h)
    {
        item.GetComponent<Image>().enabled = h;
        item.GetComponent<Image>().raycastTarget = h;
        foreach (Transform t in item.transform)
            if (t.GetComponent<Image>() != null)
                t.GetComponent<Image>().enabled = h;
    }
    internal void insantiateGUI(Item itemStorage)
    {
        Debug.Log(itemStorage.name);
        if (itemStorage.transform.eulerAngles != Vector3.zero) return;
        itemStorage.isShowing = true;
        itemStorage.GetComponent<Image>().color = new Color(1, 1, 1, 0.5f);
        foreach (Item it in itemStorage.itemHelds)
            itemVisualToggle(it, true);
        foreach (ItemSpot iS in itemStorage.mySpots)
            iS.GetComponent<Image>().enabled = true;
        ///toolbar add
        Image cd = Instantiate(prefabToolBar,
                Input.mousePosition,
                  Quaternion.identity, itemStorage.transform);
        cd.rectTransform.localPosition =
            new Vector3(0, (((float)itemStorage.size.y) / 2) * spotSize + toolbarHeight / 2);
        cd.rectTransform.sizeDelta = new Vector2((float)itemStorage.size.x * spotSize, toolbarHeight);
        cd.transform.GetChild(1).GetComponent<Button>().onClick.AddListener(() =>
        {
            itemStorage.isShowing = false;
            itemStorage.GetComponent<Image>().color = Color.white;
            foreach (Item it in itemStorage.itemHelds)
                itemVisualToggle(it, false);
            foreach (ItemSpot iS in itemStorage.mySpots)
                iS.GetComponent<Image>().enabled = false;
            Destroy(cd.gameObject);
        });
    }
    void generateItem(Item prefab)
    {
        Vector2Int size = new Vector2Int(UnityEngine.Random.Range(1, 6), UnityEngine.Random.Range(1, 6));
        Item c = Instantiate(prefab, imagePosition(size), Quaternion.identity, itemsTransform);
        c.size = size;
        c.mySpots = new List<ItemSpot>();
        Instantiate(prefabBackground, imagePosition(size), Quaternion.identity, c.transform)
            .GetComponent<RectTransform>().sizeDelta =
            new Vector2((float)c.size.x * spotSize, c.size.y * spotSize);
        //backGroundSet(c);
        for (int x = 0; x < c.size.x; x++)
            for (int y = 0; y < c.size.y; y++)
            {
                Image cd = Instantiate(prefabSpot, Input.mousePosition, Quaternion.identity, c.transform);
                cd.rectTransform.localPosition =
                    new Vector3(x + 0.5f - ((float)c.size.x) / 2, y + 0.5f - ((float)c.size.y) / 2) * spotSize;
                cd.rectTransform.sizeDelta = Vector2.one * spotSize;
                cd.color = new Color(1, 1, 1, c.canStore ? 0.25f : 0.01f);
                c.mySpots.Add(cd.GetComponent<ItemSpot>());
                cd.enabled = false;
                // prefab.setSpot(cd.GetComponent<ItemSpot>());
                // c.GetComponent<ItemSpot>().canStore = t.canStore;
            }
        if (c.canStore) c.itemHelds = new List<Item>();
        // Debug.Log(prefab.mySpots.Count);
    }
    #endregion
}