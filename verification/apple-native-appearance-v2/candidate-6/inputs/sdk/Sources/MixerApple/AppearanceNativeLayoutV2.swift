#if canImport(UIKit)
import UIKit
import MixerUI

/// Bounded concrete UIKit layout for the closed V2 recipes. This is not an app
/// extensible layout language. Every measurement happens on detached controls.
@MainActor final class AppearanceNativeLayoutV2 {
    struct Placement { let key: String; let parent: String; var frame: CGRect; let index: Int }
    let plan: UIResolvedAppearancePlanV2
    var records: [String: AppearanceNodeViewV2] = [:]
    var decorations: [String: UIView] = [:]
    var placements: [Placement] = []
    var navigation: (key: String, expanded: CGFloat, compact: CGFloat, expandedLabel: CGRect, compactLabel: CGRect)?
    private let rtl: Bool
    init(plan: UIResolvedAppearancePlanV2) {
        self.plan = plan; rtl = plan.environment.direction == .rightToLeft
        for node in plan.nodes {
            let view = AppearanceNodeViewV2(node: node, plan: plan)
            view.density = plan.environment.density1024
            view.semanticContentAttribute = rtl ? .forceRightToLeft : .forceLeftToRight
            records[node.identity.id] = view
        }
    }
    private func p(_ x: UInt32) -> CGFloat { AppearanceNativeMathV2.points(x) }
    private func q(_ x: CGFloat) throws -> CGFloat { try AppearanceNativeMathV2.extent(x) }
    private func checked(_ value: CGFloat) throws -> CGFloat {
        guard value.isFinite, value >= 0, value <= CGFloat(UIAppearanceGeometryV2.maximumExtent64)/64 else { throw UIAppearanceErrorV2.layout }
        return try q(value)
    }
    private func horizontal(_ align: UIHorizontalAlignmentV1, _ width: CGFloat, _ child: CGFloat) -> CGFloat {
        switch align { case .center: return (width-child)/2; case .leading: return rtl ? width-child : 0; case .trailing: return rtl ? 0 : width-child }
    }
    private func add(_ key: String, parent: String, frame: CGRect) {
        let index = placements.filter { $0.parent == parent }.count
        placements.append(Placement(key: key, parent: parent, frame: frame, index: index))
    }
    private func configureLabel(_ label: UILabel, _ text: UIResolvedTextV2, width: CGFloat) throws -> (CGSize, CGFloat?, CGFloat?) {
        label.font = AppearanceNativeMathV2.font(text); label.text = text.value
        label.numberOfLines = text.maximumLines ?? 0
        label.textAlignment = rtl ? .right : .left
        return try measure(text, width: width)
    }
    private func measure(_ text: UIResolvedTextV2, width: CGFloat) throws -> (CGSize, CGFloat?, CGFloat?) {
        guard width.isFinite, width >= 0 else { throw UIAppearanceErrorV2.layout }
        guard !text.value.isEmpty else { return (.zero, nil, nil) }
        guard width > 0 else { throw UIAppearanceErrorV2.layout }
        let style = NSMutableParagraphStyle(); style.lineBreakMode = .byWordWrapping
        style.baseWritingDirection = rtl ? .rightToLeft : .leftToRight
        let storage = NSTextStorage(string: text.value, attributes: [.font: AppearanceNativeMathV2.font(text), .paragraphStyle: style])
        let manager = NSLayoutManager(); let container = NSTextContainer(size: CGSize(width: width, height: CGFloat.greatestFiniteMagnitude))
        container.lineFragmentPadding = 0; container.maximumNumberOfLines = text.maximumLines ?? 0
        container.lineBreakMode = .byTruncatingTail
        manager.addTextContainer(container); storage.addLayoutManager(manager)
        let glyphs = manager.glyphRange(for: container)
        let used = manager.usedRect(for: container)
        var first: CGFloat?, last: CGFloat?
        manager.enumerateLineFragments(forGlyphRange: glyphs) { line, _, _, range, _ in
            guard range.length > 0 else { return }
            let baseline = line.minY + manager.location(forGlyphAt: range.location).y
            if first == nil { first = baseline }; last = baseline
        }
        let size = CGSize(width: try checked(min(width, max(used.maxX, 0))), height: try checked(max(used.maxY, 0)))
        guard size.height > 0, first != nil else { throw UIAppearanceErrorV2.layout }
        return (size, first, last)
    }
    private func text(_ record: AppearanceNodeViewV2, _ value: UIResolvedTextV2, width: CGFloat) throws -> CGSize {
        let (size, first, last) = try configureLabel(record.label, value, width: width)
        record.label.frame = CGRect(origin: .zero, size: size)
        if let view = record.selectable {
            view.text = value.value; view.font = AppearanceNativeMathV2.font(value)
            view.textContainer.maximumNumberOfLines = value.maximumLines ?? 0
            view.textContainer.lineBreakMode = .byTruncatingTail; view.frame = CGRect(origin: .zero, size: size)
        }
        record.firstBaseline = first; record.lastBaseline = last
        return size
    }

    func prepare(rootID: String, editing: [String: String], scrollOffsets: [String:CGPoint]) throws {
        let env = plan.environment
        let inset = AppearanceNativeMathV2.insets(env.safeArea64, rtl: rtl)
        let width = p(env.viewport.width64)-inset.left-inset.right
        let height = p(env.viewport.height64)-inset.top-inset.bottom
        guard width > 0, height > 0 else { throw UIAppearanceErrorV2.layout }
        _ = try layout(rootID, width: width, height: height, editing: editing)
        guard let root = records[rootID] else { throw UIAppearanceErrorV2.shape }
        let rootHeight = root.kind == .list || root.kind == .navigation ? height : root.frame.height
        guard rootHeight <= height else { throw UIAppearanceErrorV2.layout }
        add(rootID, parent: "$root", frame: CGRect(x: inset.left, y: inset.top, width: root.frame.width, height: rootHeight))
        if let navigation, let offset = scrollOffsets.values.first {
            let overflow = navigation.expanded-navigation.compact
            if overflow <= 0 || offset.y >= overflow, let record = records[navigation.key],
               case let .navigation(recipe) = record.node.recipe, let child = record.node.childIDs.first {
                record.label.font = recipe.compactTitle.map(AppearanceNativeMathV2.font)
                record.label.text = recipe.compactTitle?.value; record.label.numberOfLines = 1
                record.label.frame = navigation.compactLabel
                for index in placements.indices where placements[index].key == child && placements[index].parent == navigation.key {
                    placements[index].frame.origin.y = navigation.compact
                    placements[index].frame.size.height = record.frame.height-navigation.compact
                }
                records[child]?.scroll?.frame.size.height = record.frame.height-navigation.compact
            }
        }
        // Paint only after final row/visual geometry is known.
        for view in records.values { try view.repaint() }
        for placement in placements {
            let child = view(placement.key), parent = view(placement.parent)
            child.frame = placement.frame; parent.addSubview(child)
        }
    }
    let detachedRoot = UIView()
    func view(_ key: String) -> UIView {
        if key == "$root" { return detachedRoot }
        if key.hasPrefix("$scroll:") { return records[String(key.dropFirst(8))]!.scroll! }
        return records[key] ?? decorations[key]!
    }

    private func layout(_ id: String, width: CGFloat, height: CGFloat, editing: [String: String], row: Bool = false) throws -> CGSize {
        guard let record = records[id], width >= 0 else { throw UIAppearanceErrorV2.shape }
        let node = record.node
        record.semanticSize = .zero; record.contentRect = .zero; record.firstBaseline = nil; record.lastBaseline = nil
        var size = CGSize.zero
        switch node.recipe {
        case let .text(value): size = try text(record, value, width: width)
        case let .button(_, value, metrics):
            let inset = AppearanceNativeMathV2.insets(metrics.labelInsets64, rtl: rtl)
            let measured = try measure(value, width: width-inset.left-inset.right)
            let semantic = CGSize(width: measured.0.width+inset.left+inset.right, height: measured.0.height+inset.top+inset.bottom)
            guard width >= p(metrics.minimumHitWidth64) else { throw UIAppearanceErrorV2.layout }
            size = CGSize(width: min(width, max(semantic.width, p(metrics.minimumHitWidth64))), height: row ? semantic.height : max(semantic.height, p(metrics.minimumHitHeight64)))
            record.semanticSize = semantic
            let button = record.button!; button.titleLabel?.font = AppearanceNativeMathV2.font(value); button.setTitle(value.value, for: .normal)
            button.contentEdgeInsets = inset; button.frame = CGRect(origin: .zero, size: CGSize(width: size.width, height: max(size.height, p(metrics.minimumHitHeight64))))
            button.frame.origin.y = (size.height-button.frame.height)/2
            record.visualRect = CGRect(x: 0, y: (size.height-semantic.height)/2, width: size.width, height: semantic.height)
            record.firstBaseline = measured.1.map { $0 + inset.top }; record.lastBaseline = measured.2.map { $0 + inset.top }
        case let .textField(label, value, valueText, metrics):
            let inset = AppearanceNativeMathV2.insets(metrics.insets64, rtl: rtl)
            let font = AppearanceNativeMathV2.font(valueText)
            let display = editing[id] ?? value
            // UITextField is natively single line; measure native script fallback
            // using the exact font instead of a fixed Latin line box.
            let storage = NSAttributedString(string: display.isEmpty ? label : display, attributes: [.font: font])
            let bounds = storage.boundingRect(with: CGSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude), options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)
            let contentHeight = max(try checked(bounds.height), p(metrics.minimumContentHeight64))
            let semantic = CGSize(width: width, height: contentHeight+inset.top+inset.bottom)
            size = CGSize(width: width, height: row ? semantic.height : max(semantic.height, p(metrics.minimumHitHeight64)))
            record.semanticSize = semantic; record.visualRect = CGRect(x: 0, y: (size.height-semantic.height)/2, width: width, height: semantic.height)
            let field = record.field!; field.font = font; field.text = display; field.textAlignment = rtl ? .right : .left
            field.accessibilityLabel = label; field.authoredInsets = inset
            field.frame = CGRect(x: 0, y: (size.height-max(size.height,p(metrics.minimumHitHeight64)))/2, width: width, height: max(size.height,p(metrics.minimumHitHeight64)))
            // UITextField does not expose its actual first/last shaped baseline
            // as a scalar. This bounded consumer rejects required baseline use
            // rather than substituting a Latin font ascender for native layout.
            record.firstBaseline = nil; record.lastBaseline = nil
        case let .toggle(value, checked, metrics):
            let trackWidth = p(metrics.trackWidth64), gap = p(metrics.labelGap64)
            let labelWidth = width-trackWidth-gap
            guard labelWidth >= 0, width >= p(metrics.minimumHitWidth64) else { throw UIAppearanceErrorV2.layout }
            let label = try text(record, value, width: labelWidth)
            record.semanticSize = label
            size = CGSize(width: width, height: row ? label.height : max(label.height, p(metrics.minimumHitHeight64), p(metrics.trackHeight64)))
            record.label.frame.origin = CGPoint(x: rtl ? trackWidth+gap : 0, y: (size.height-label.height)/2)
            record.visualRect = CGRect(x: rtl ? 0 : width-trackWidth, y: (size.height-p(metrics.trackHeight64))/2, width: trackWidth, height: p(metrics.trackHeight64))
            let control = record.toggle!; control.setOn(checked, animated: false); control.accessibilityLabel = value.value
            control.frame = CGRect(x: record.visualRect.minX, y: (size.height-p(metrics.minimumHitHeight64))/2, width: max(trackWidth,p(metrics.minimumHitWidth64)), height: p(metrics.minimumHitHeight64))
        case let .vStack(gaps, alignment):
            size = try vertical(record, width: width, height: height, gaps: gaps, alignment: alignment, editing: editing, semanticRow: row)
        case let .section(section):
            switch section.context {
            case .listGroup: throw UIAppearanceErrorV2.layout // List owns this structural record below.
            case .outsideList, .withinListRow:
                var headerHeight: CGFloat = 0
                if let header = section.header { headerHeight = try text(record, header, width: width).height }
                let content = try vertical(record, width: width, height: height, gaps: section.contentGaps64, alignment: section.alignment, editing: editing,
                    offset: headerHeight + (headerHeight > 0 && !node.childIDs.isEmpty ? p(section.headerToContentGap64) : 0), semanticRow: row)
                size = CGSize(width: max(record.label.frame.width, content.width), height: max(headerHeight,content.height))
            }
        case let .hStack(gaps, alignment):
            let gap = gaps.reduce(CGFloat(0)) { $0+p($1) }
            guard width >= gap else { throw UIAppearanceErrorV2.layout }
            let placementStart = placements.count
            var children = try node.childIDs.map { try layout($0,width:width,height:height,editing:editing,row:row) }
            if children.reduce(CGFloat(0), { $0+$1.width })+gap > width, !children.isEmpty {
                placements.removeSubrange(placementStart..<placements.count)
                let available = try UIAppearanceGeometryV2.measuredExtent64(Double(width-gap))
                let count = UInt32(children.count), quotient = available/count, remainder = available%count
                children = try node.childIDs.enumerated().map { index,id in
                    try layout(id,width:p(quotient+(UInt32(index)<remainder ? 1 : 0)),height:height,editing:editing,row:row)
                }
            }
            let h = children.map(\.height).max() ?? 0
            var baseline: CGFloat?; var finalHeight = h
            if alignment == .firstTextBaseline || alignment == .lastTextBaseline {
                let values = node.childIDs.map { alignment == .firstTextBaseline ? records[$0]!.firstBaseline : records[$0]!.lastBaseline }
                guard values.allSatisfy({ $0 != nil }) else { throw UIAppearanceErrorV2.unsupportedNativeOperation }
                baseline = values.compactMap { $0 }.max()
                for (index, value) in values.enumerated() { finalHeight = max(finalHeight, baseline! - value! + children[index].height) }
            }
            size = CGSize(width: children.reduce(gap, { $0+$1.width }), height: finalHeight)
            var x: CGFloat = 0
            for (index, child) in node.childIDs.enumerated() {
                let childSize = children[index]
                let y: CGFloat
                switch alignment {
                case .top: y = 0
                case .center: y = (finalHeight-childSize.height)/2
                case .bottom: y = finalHeight-childSize.height
                case .firstTextBaseline: y = baseline!-records[child]!.firstBaseline!
                case .lastTextBaseline: y = baseline!-records[child]!.lastBaseline!
                }
                add(child,parent:id,frame:CGRect(x:rtl ? size.width-x-childSize.width : x,y:y,width:childSize.width,height:childSize.height))
                x += childSize.width + (index < gaps.count ? p(gaps[index]) : 0)
            }
            record.firstBaseline = baseline; record.lastBaseline = baseline
        case let .zStack(alignment):
            let children = try node.childIDs.map { try layout($0,width:width,height:height,editing:editing,row:row) }
            size = CGSize(width: children.map(\.width).max() ?? 0, height: children.map(\.height).max() ?? 0)
            for (index, child) in node.childIDs.enumerated() {
                let childSize = children[index]
                let horizontalAlignment: UIHorizontalAlignmentV1 = switch alignment { case .leading,.topLeading,.bottomLeading: .leading; case .trailing,.topTrailing,.bottomTrailing: .trailing; default: .center }
                let y: CGFloat = switch alignment { case .top,.topLeading,.topTrailing: 0; case .bottom,.bottomLeading,.bottomTrailing: size.height-childSize.height; default: (size.height-childSize.height)/2 }
                add(child,parent:id,frame:CGRect(x:horizontal(horizontalAlignment,size.width,childSize.width),y:y,width:childSize.width,height:childSize.height))
            }
        case let .list(list): size = try layoutList(record,list,width:width,height:height,editing:editing)
        case let .navigation(navigation):
            let expandedInsets = AppearanceNativeMathV2.insets(navigation.metrics.expandedInsets64,rtl:rtl)
            let compactInsets = AppearanceNativeMathV2.insets(navigation.metrics.compactInsets64,rtl:rtl)
            let expanded = try navigation.expandedTitle.map { try text(record,$0,width:width-expandedInsets.left-expandedInsets.right) } ?? .zero
            let compact = try navigation.compactTitle.map { try measure($0,width:width-compactInsets.left-compactInsets.right).0 } ?? .zero
            let compactHeight = max(p(navigation.metrics.minimumCompactBar64),compact.height+compactInsets.top+compactInsets.bottom)
            let expandedHeight = expanded.height > 0 ? max(p(navigation.metrics.minimumExpandedBar64),compactHeight+expanded.height+expandedInsets.top+expandedInsets.bottom) : compactHeight
            guard expandedHeight <= height, let child = node.childIDs.first else { throw UIAppearanceErrorV2.layout }
            let expandedRect = CGRect(x:expandedInsets.left+horizontal(navigation.metrics.expandedAlignment,width-expandedInsets.left-expandedInsets.right,expanded.width),y:compactHeight+expandedInsets.top,width:expanded.width,height:expanded.height)
            let compactRect = CGRect(x:compactInsets.left+horizontal(navigation.metrics.compactAlignment,width-compactInsets.left-compactInsets.right,compact.width),y:compactInsets.top+(compactHeight-compactInsets.top-compactInsets.bottom-compact.height)/2,width:compact.width,height:compact.height)
            record.label.frame = expandedRect
            self.navigation = (id,expandedHeight,compactHeight,expandedRect,compactRect)
            _ = try layout(child,width:width,height:height-expandedHeight,editing:editing)
            add(child,parent:id,frame:CGRect(x:0,y:expandedHeight,width:records[child]!.frame.width,height:records[child]!.frame.height))
            size = CGSize(width:width,height:height)
        }
        size = CGSize(width:try checked(size.width),height:try checked(size.height))
        record.frame = CGRect(origin:.zero,size:size)
        if record.semanticSize == .zero { record.semanticSize = size }
        if record.contentRect == .zero { record.contentRect = CGRect(origin:.zero,size:record.semanticSize) }
        if record.firstBaseline == nil, let first = node.childIDs.first, let b = records[first]?.firstBaseline,
           let placement = placements.first(where: { $0.key == first && $0.parent == id }) { record.firstBaseline = b+placement.frame.minY }
        if record.lastBaseline == nil, let last = node.childIDs.last, let b = records[last]?.lastBaseline,
           let placement = placements.first(where: { $0.key == last && $0.parent == id }) { record.lastBaseline = b+placement.frame.minY }
        return size
    }

    private func vertical(_ record: AppearanceNodeViewV2,width:CGFloat,height:CGFloat,gaps:[UInt32],alignment:UIHorizontalAlignmentV1,editing:[String:String],offset:CGFloat = 0,semanticRow:Bool = false) throws -> CGSize {
        guard gaps.count == max(0,record.node.childIDs.count-1) else { throw UIAppearanceErrorV2.shape }
        var y = offset, w: CGFloat = 0
        var children: [(String,CGSize,CGFloat)] = []
        for (index, id) in record.node.childIDs.enumerated() {
            let size = try layout(id,width:width,height:height,editing:editing,row:semanticRow)
            children.append((id,size,y)); y = try checked(y+size.height+(index<gaps.count ? p(gaps[index]) : 0)); w = max(w,size.width)
        }
        for (id,size,y) in children { add(id,parent:record.identity.id,frame:CGRect(x:horizontal(alignment,w,size.width),y:y,width:size.width,height:size.height)) }
        return CGSize(width:w,height:y)
    }

    private func layoutList(_ record: AppearanceNodeViewV2,_ list:UIResolvedListV2,width:CGFloat,height:CGFloat,editing:[String:String]) throws -> CGSize {
        let id = record.identity.id, parent = "$scroll:"+id, metrics = list.metrics
        let outer = p(metrics.outerHorizontal64), groupWidth = width-2*outer
        let insets = AppearanceNativeMathV2.insets(metrics.contentInsets64,rtl:rtl)
        let contentWidth = groupWidth-insets.left-insets.right
        guard contentWidth > 0 else { throw UIAppearanceErrorV2.layout }
        var y: CGFloat = 0
        guard case let .list(_,surface,separator) = plan.style(nodeID:id)!.paints else { throw UIAppearanceErrorV2.shape }
        for (groupIndex, group) in list.groups.enumerated() {
            let groupKey = "$group:\(id):\(groupIndex)"
            guard group.visible else {
                if case let .section(identity) = group.source { add(identity.id,parent:parent,frame:.zero) }
                continue
            }
            y = try checked(y+p(group.leadingGap64))
            if let header = group.header {
                let headerView = UILabel(); headerView.backgroundColor = .clear; headerView.adjustsFontForContentSizeCategory = false
                let measured = try configureLabel(headerView,header,width:groupWidth)
                if case let .section(source) = group.source, case let .section(paint,_) = plan.style(nodeID:source.id)!.paints { headerView.textColor = paint.map(AppearanceNativeMathV2.color) }
                let key = "$header:\(id):\(groupIndex)"; decorations[key] = headerView
                add(key,parent:parent,frame:CGRect(x:outer,y:y,width:groupWidth,height:measured.0.height)); y += measured.0.height
                y = try checked(y+p(group.headerToRowsGap64))
            }
            let groupView = AppearancePaintViewV2(); groupView.density = plan.environment.density1024
            decorations[groupKey] = groupView
            var rowY: CGFloat = 0, separators: [CGFloat] = []
            let rowsParent: String
            if case let .section(source) = group.source { rowsParent = source.id } else { rowsParent = groupKey }
            for (index, row) in group.rowIdentities.enumerated() {
                let measured = try layout(row.id,width:contentWidth,height:height,editing:editing,row:true)
                let node = records[row.id]!
                let semantic = node.semanticSize.height
                let rowHeight = try checked(max(p(list.rowHeightFloor64),semantic+insets.top+insets.bottom))
                if case let .toggle(_,_,toggleMetrics) = node.node.recipe, rowHeight < p(toggleMetrics.trackHeight64) { throw UIAppearanceErrorV2.layout }
                let dy = (rowHeight-measured.height)/2
                for subview in node.subviews { subview.frame = subview.frame.offsetBy(dx:insets.left,dy:dy) }
                node.visualRect = node.visualRect.offsetBy(dx:insets.left,dy:dy)
                node.contentRect = CGRect(x:insets.left,y:(rowHeight-semantic)/2,width:contentWidth,height:semantic)
                for placementIndex in placements.indices where placements[placementIndex].parent == row.id { placements[placementIndex].frame = placements[placementIndex].frame.offsetBy(dx:insets.left,dy:dy) }
                node.firstBaseline = node.firstBaseline.map { $0+dy }; node.lastBaseline = node.lastBaseline.map { $0+dy }
                add(row.id,parent:rowsParent,frame:CGRect(x:0,y:rowY,width:groupWidth,height:rowHeight))
                rowY += rowHeight
                if index+1 < group.rowIdentities.count { separators.append(rowY) }
            }
            let path = try AppearanceNativeMathV2.outlinePath(CGRect(x:0,y:0,width:groupWidth,height:rowY),radius:metrics.radius64,density:plan.environment.density1024)
            groupView.shapes = [.init(path:path,fill:AppearanceNativeMathV2.color(surface),stroke:nil,width:0)]
            // One physical-pixel mask, inverse transformed exactly once.
            let mask = CAShapeLayer(); mask.path = path; mask.fillRule = .nonZero
            mask.setAffineTransform(CGAffineTransform(scaleX:1024/CGFloat(plan.environment.density1024),y:1024/CGFloat(plan.environment.density1024)))
            groupView.layer.mask = mask
            for (index,boundary) in separators.enumerated() {
                let key = "$separator:\(id):\(groupIndex):\(index)"
                let view = UIView(); view.backgroundColor = AppearanceNativeMathV2.color(separator); decorations[key] = view
                let thickness = p(metrics.separatorThickness64), inset = p(metrics.separatorInset64)
                guard groupWidth >= 2*inset else { throw UIAppearanceErrorV2.layout }
                add(key,parent:groupKey,frame:CGRect(x:inset,y:boundary-thickness/2,width:groupWidth-2*inset,height:thickness))
            }
            if case let .section(source) = group.source {
                let section = records[source.id]!; section.label.isHidden = true; section.semanticSize = CGSize(width:groupWidth,height:rowY)
                add(source.id,parent:groupKey,frame:CGRect(x:0,y:0,width:groupWidth,height:rowY))
            }
            add(groupKey,parent:parent,frame:CGRect(x:outer,y:y,width:groupWidth,height:rowY)); y = try checked(y+rowY)
        }
        y = try checked(y+p(list.trailingPadding64))
        record.scroll!.frame = CGRect(x:0,y:0,width:width,height:height)
        record.scroll!.contentSize = CGSize(width:width,height:y)
        return CGSize(width:width,height:height)
    }
}
#endif
